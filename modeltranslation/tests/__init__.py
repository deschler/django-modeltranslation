# -*- coding: utf-8 -*-
from __future__ import with_statement  # Python 2.5 compatibility
import datetime
from decimal import Decimal
import os
import shutil
import imp

from django import forms
from django.conf import settings as django_settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.db.models import Q, F
from django.db.models.loading import AppCache
from django.test import TestCase
from django.utils import six
from django.utils.translation import get_language, trans_real

from modeltranslation import settings as mt_settings
from modeltranslation import translator
from modeltranslation import admin
from modeltranslation.models import autodiscover
from modeltranslation.tests import models
from modeltranslation.tests.translation import (FallbackModel2TranslationOptions,
                                                FieldInheritanceCTranslationOptions,
                                                FieldInheritanceETranslationOptions)
from modeltranslation.tests.test_settings import TEST_SETTINGS
from modeltranslation.utils import (build_css_class, build_localized_fieldname,
                                    auto_populate, fallbacks)

try:
    from django.test.utils import override_settings
except ImportError:
    from modeltranslation.tests.utils import override_settings
try:
    from django.utils.translation import override
except ImportError:
    from modeltranslation.tests.utils import override  # NOQA

# None of the following tests really depend on the content of the request,
# so we'll just pass in None.
request = None

# How many models are registered for tests.
TEST_MODELS = 24


class reload_override_settings(override_settings):
    """Context manager that not only override settings, but also reload modeltranslation conf."""
    def __enter__(self):
        super(reload_override_settings, self).__enter__()
        imp.reload(mt_settings)

    def __exit__(self, exc_type, exc_value, traceback):
        super(reload_override_settings, self).__exit__(exc_type, exc_value, traceback)
        imp.reload(mt_settings)


# In this test suite fallback language is turned off. This context manager temporarily turns it on.
def default_fallback():
    return reload_override_settings(
        MODELTRANSLATION_FALLBACK_LANGUAGES=(mt_settings.DEFAULT_LANGUAGE,))


class ModeltranslationTestBase(TestCase):
    urls = 'modeltranslation.tests.urls'
    cache = AppCache()
    synced = False

    @classmethod
    def setUpClass(cls):
        """
        Prepare database:
        * Call syncdb to create tables for tests.models (since during
        default testrunner's db creation modeltranslation.tests was not in INSTALLED_APPS
        """
        super(ModeltranslationTestBase, cls).setUpClass()
        if not ModeltranslationTestBase.synced:
            # In order to perform only one syncdb
            ModeltranslationTestBase.synced = True
            with override_settings(**TEST_SETTINGS):
                import sys

                # 1. Reload translation in case USE_I18N was False
                from django.utils import translation
                imp.reload(translation)

                # 2. Reload MT because LANGUAGES likely changed.
                imp.reload(mt_settings)
                imp.reload(translator)
                imp.reload(admin)

                # 3. Reset test models (because autodiscover have already run, those models
                #    have translation fields, but for languages previously defined. We want
                #    to be sure that 'de' and 'en' are available)
                del cls.cache.app_models['tests']
                imp.reload(models)
                cls.cache.load_app('modeltranslation.tests')
                sys.modules.pop('modeltranslation.tests.translation', None)

                # 4. Autodiscover
                from modeltranslation import models as aut_models
                imp.reload(aut_models)

                # 5. Syncdb (``migrate=False`` in case of south)
                from django.db import connections, DEFAULT_DB_ALIAS
                call_command('syncdb', verbosity=0, migrate=False, interactive=False,
                             database=connections[DEFAULT_DB_ALIAS].alias, load_initial_data=False)

    def setUp(self):
        self._old_language = get_language()
        trans_real.activate('de')

    def tearDown(self):
        trans_real.activate(self._old_language)

ModeltranslationTestBase = override_settings(**TEST_SETTINGS)(ModeltranslationTestBase)


class TestAutodiscover(ModeltranslationTestBase):
    # The way the ``override_settings`` works on ``TestCase`` is wicked;
    # it patches ``_pre_setup`` and ``_post_teardown`` methods.
    # Because of this, if class B extends class A and both are ``override_settings``'ed,
    # class B settings would be overwritten by class A settings (if some keys clash).
    # To solve this, override some settings after parents ``_pre_setup`` is called.
    def _pre_setup(self):
        super(TestAutodiscover, self)._pre_setup()
        # Add test_app to INSTALLED_APPS
        new_installed_apps = django_settings.INSTALLED_APPS + ('modeltranslation.tests.test_app',)
        self.__override = override_settings(INSTALLED_APPS=new_installed_apps)
        self.__override.enable()

    def _post_teardown(self):
        self.__override.disable()
        imp.reload(mt_settings)  # restore mt_settings.FALLBACK_LANGUAGES
        super(TestAutodiscover, self)._post_teardown()

    @classmethod
    def setUpClass(cls):
        """Save registry (and restore it after tests)."""
        super(TestAutodiscover, cls).setUpClass()
        from copy import copy
        from modeltranslation.translator import translator
        cls.registry_cpy = copy(translator._registry)

    @classmethod
    def tearDownClass(cls):
        from modeltranslation.translator import translator
        translator._registry = cls.registry_cpy
        super(TestAutodiscover, cls).tearDownClass()

    def tearDown(self):
        import sys
        # Rollback model classes
        del self.cache.app_models['test_app']
        from .test_app import models
        imp.reload(models)
        # Delete translation modules from import cache
        sys.modules.pop('modeltranslation.tests.test_app.translation', None)
        sys.modules.pop('modeltranslation.tests.project_translation', None)
        super(TestAutodiscover, self).tearDown()

    def check_news(self):
        from .test_app.models import News
        fields = dir(News())
        self.assertIn('title', fields)
        self.assertIn('title_en', fields)
        self.assertIn('title_de', fields)
        self.assertIn('visits', fields)
        self.assertNotIn('visits_en', fields)
        self.assertNotIn('visits_de', fields)

    def check_other(self, present=True):
        from .test_app.models import Other
        fields = dir(Other())
        self.assertIn('name', fields)
        if present:
            self.assertIn('name_en', fields)
            self.assertIn('name_de', fields)
        else:
            self.assertNotIn('name_en', fields)
            self.assertNotIn('name_de', fields)

    def test_simple(self):
        """Check if translation is imported for installed apps."""
        autodiscover()
        self.check_news()
        self.check_other(present=False)

    @reload_override_settings(
        MODELTRANSLATION_TRANSLATION_FILES=('modeltranslation.tests.project_translation',)
    )
    def test_global(self):
        """Check if translation is imported for global translation file."""
        autodiscover()
        self.check_news()
        self.check_other()

    @reload_override_settings(
        MODELTRANSLATION_TRANSLATION_FILES=('modeltranslation.tests.test_app.translation',)
    )
    def test_duplication(self):
        """Check if there is no problem with duplicated filenames."""
        autodiscover()
        self.check_news()


class ModeltranslationTest(ModeltranslationTestBase):
    """Basic tests for the modeltranslation application."""
    def test_registration(self):
        langs = tuple(l[0] for l in django_settings.LANGUAGES)
        self.assertEqual(langs, tuple(mt_settings.AVAILABLE_LANGUAGES))
        self.assertEqual(2, len(langs))
        self.assertTrue('de' in langs)
        self.assertTrue('en' in langs)
        self.assertTrue(translator.translator)

        # Check that all models are registered for translation
        self.assertEqual(len(translator.translator.get_registered_models()), TEST_MODELS)

        # Try to unregister a model that is not registered
        self.assertRaises(translator.NotRegistered,
                          translator.translator.unregister, models.BasePage)

        # Try to get options for a model that is not registered
        self.assertRaises(translator.NotRegistered,
                          translator.translator.get_options_for_model, User)

        # Ensure that a base can't be registered after a subclass.
        self.assertRaises(translator.DescendantRegistered,
                          translator.translator.register, models.BasePage)

        # Or unregistered before it.
        self.assertRaises(translator.DescendantRegistered,
                          translator.translator.unregister, models.Slugged)

    def test_fields(self):
        field_names = dir(models.TestModel())
        self.assertTrue('id' in field_names)
        self.assertTrue('title' in field_names)
        self.assertTrue('title_de' in field_names)
        self.assertTrue('title_en' in field_names)
        self.assertTrue('text' in field_names)
        self.assertTrue('text_de' in field_names)
        self.assertTrue('text_en' in field_names)
        self.assertTrue('url' in field_names)
        self.assertTrue('url_de' in field_names)
        self.assertTrue('url_en' in field_names)
        self.assertTrue('email' in field_names)
        self.assertTrue('email_de' in field_names)
        self.assertTrue('email_en' in field_names)

    def test_verbose_name(self):
        verbose_name = models.TestModel._meta.get_field('title_de').verbose_name
        self.assertEquals(six.text_type(verbose_name), u'title [de]')

    def test_descriptor_introspection(self):
        # See Django #8248
        try:
            models.TestModel.title
            models.TestModel.title.__doc__
            self.assertTrue(True)
        except:
            self.fail('Descriptor accessed on class should return itself.')

    def test_fields_hashes(self):
        opts = models.TestModel._meta
        orig = opts.get_field('title')
        en = opts.get_field('title_en')
        de = opts.get_field('title_de')
        # Translation field retain creation_counters
        self.assertEqual(orig.creation_counter, en.creation_counter)
        self.assertEqual(orig.creation_counter, de.creation_counter)
        # But they compare unequal
        self.assertNotEqual(orig, en)
        self.assertNotEqual(orig, de)
        self.assertNotEqual(en, de)
        # Their hashes too
        self.assertNotEqual(hash(orig), hash(en))
        self.assertNotEqual(hash(orig), hash(de))
        self.assertNotEqual(hash(en), hash(de))
        self.assertEqual(3, len(set([orig, en, de])))
        # TranslationFields can compare equal if they have the same language
        de.language = 'en'
        self.assertNotEqual(orig, de)
        self.assertEqual(en, de)
        self.assertEqual(hash(en), hash(de))
        self.assertEqual(2, len(set([orig, en, de])))
        de.language = 'de'

    def test_set_translation(self):
        """This test briefly shows main modeltranslation features."""
        self.assertEqual(get_language(), 'de')
        title_de = "title de"
        title_en = "title en"

        # The original field "title" passed in the constructor is
        # populated for the current language field: "title_de".
        inst2 = models.TestModel(title=title_de)
        self.assertEqual(inst2.title, title_de)
        self.assertEqual(inst2.title_en, None)
        self.assertEqual(inst2.title_de, title_de)

        # So creating object is language-aware
        with override('en'):
            inst2 = models.TestModel(title=title_en)
            self.assertEqual(inst2.title, title_en)
            self.assertEqual(inst2.title_en, title_en)
            self.assertEqual(inst2.title_de, None)

        # Value from original field is presented in current language:
        inst2 = models.TestModel(title_de=title_de, title_en=title_en)
        self.assertEqual(inst2.title, title_de)
        with override('en'):
            self.assertEqual(inst2.title, title_en)

        # Changes made via original field affect current language field:
        inst2.title = 'foo'
        self.assertEqual(inst2.title, 'foo')
        self.assertEqual(inst2.title_en, title_en)
        self.assertEqual(inst2.title_de, 'foo')
        with override('en'):
            inst2.title = 'bar'
            self.assertEqual(inst2.title, 'bar')
            self.assertEqual(inst2.title_en, 'bar')
            self.assertEqual(inst2.title_de, 'foo')
        self.assertEqual(inst2.title, 'foo')

        # When conflict, language field wins with original field
        inst2 = models.TestModel(title='foo', title_de=title_de, title_en=title_en)
        self.assertEqual(inst2.title, title_de)
        self.assertEqual(inst2.title_en, title_en)
        self.assertEqual(inst2.title_de, title_de)

        # Creating model and assigning only one language
        inst1 = models.TestModel(title_en=title_en)
        # Please note: '' and not None, because descriptor falls back to field default value
        self.assertEqual(inst1.title, '')
        self.assertEqual(inst1.title_en, title_en)
        self.assertEqual(inst1.title_de, None)
        # Assign current language value - de
        inst1.title = title_de
        self.assertEqual(inst1.title, title_de)
        self.assertEqual(inst1.title_en, title_en)
        self.assertEqual(inst1.title_de, title_de)
        inst1.save()

        # Check that the translation fields are correctly saved and provide the
        # correct value when retrieving them again.
        n = models.TestModel.objects.get(title=title_de)
        self.assertEqual(n.title, title_de)
        self.assertEqual(n.title_en, title_en)
        self.assertEqual(n.title_de, title_de)

        # Queries are also language-aware:
        self.assertEqual(1, models.TestModel.objects.filter(title=title_de).count())
        with override('en'):
            self.assertEqual(0, models.TestModel.objects.filter(title=title_de).count())

    def test_fallback_language(self):
        # Present what happens if current language field is empty
        self.assertEqual(get_language(), 'de')
        title_de = "title de"

        # Create model with value in de only...
        inst2 = models.TestModel(title=title_de)
        self.assertEqual(inst2.title, title_de)
        self.assertEqual(inst2.title_en, None)
        self.assertEqual(inst2.title_de, title_de)

        # In this test environment, fallback language is not set. So return value for en
        # will be field's default: ''
        with override('en'):
            self.assertEqual(inst2.title, '')
            self.assertEqual(inst2.title_en, None)  # Language field access returns real value

        # However, by default FALLBACK_LANGUAGES is set to DEFAULT_LANGUAGE
        with default_fallback():

            # No change here...
            self.assertEqual(inst2.title, title_de)

            # ... but for empty en fall back to de
            with override('en'):
                self.assertEqual(inst2.title, title_de)
                self.assertEqual(inst2.title_en, None)  # Still real value

    def test_fallback_values_1(self):
        """
        If ``fallback_values`` is set to string, all untranslated fields would
        return this string.
        """
        title1_de = "title de"
        n = models.FallbackModel(title=title1_de)
        n.save()
        n = models.FallbackModel.objects.get(title=title1_de)
        self.assertEqual(n.title, title1_de)
        trans_real.activate("en")
        self.assertEqual(n.title, "fallback")

    def test_fallback_values_2(self):
        """
        If ``fallback_values`` is set to ``dict``, all untranslated fields in
        ``dict`` would return this mapped value. Fields not in ``dict`` would
        return default translation.
        """
        title1_de = "title de"
        text1_de = "text in german"
        n = models.FallbackModel2(title=title1_de, text=text1_de)
        n.save()
        n = models.FallbackModel2.objects.get(title=title1_de)
        trans_real.activate("en")
        self.assertEqual(n.title, '')  # Falling back to default field value
        self.assertEqual(
            n.text,
            FallbackModel2TranslationOptions.fallback_values['text'])

    def _compare_instances(self, x, y, field):
        self.assertEqual(getattr(x, field), getattr(y, field),
                         "Constructor diff on field %s." % field)

    def _test_constructor(self, keywords):
        n = models.TestModel(**keywords)
        m = models.TestModel.objects.create(**keywords)
        opts = translator.translator.get_options_for_model(models.TestModel)
        for base_field, trans_fields in opts.fields.items():
            self._compare_instances(n, m, base_field)
            for lang_field in trans_fields:
                self._compare_instances(n, m, lang_field.name)

    def test_constructor(self):
        """
        Ensure that model constructor behaves exactly the same as objects.create
        """
        # test different arguments compositions
        keywords = dict(
            # original only
            title='title',
            # both languages + original
            email='q@q.qq', email_de='d@d.dd', email_en='e@e.ee',
            # both languages without original
            text_en='text en', text_de='text de',
        )
        self._test_constructor(keywords)

        keywords = dict(
            # only current language
            title_de='title',
            # only not current language
            url_en='http://www.google.com',
            # original + current
            text='text def', text_de='text de',
            # original + not current
            email='q@q.qq', email_en='e@e.ee',
        )
        self._test_constructor(keywords)


class FallbackTests(ModeltranslationTestBase):
    test_fallback = {
        'default': ('de',),
        'de': ('en',)
    }

    def test_settings(self):
        # Initial
        self.assertEqual(mt_settings.FALLBACK_LANGUAGES, {'default': ()})
        # Tuple/list
        with reload_override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=('de',)):
            self.assertEqual(mt_settings.FALLBACK_LANGUAGES, {'default': ('de',)})
        # Whole dict
        with reload_override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=self.test_fallback):
            self.assertEqual(mt_settings.FALLBACK_LANGUAGES, self.test_fallback)
        # Improper language raises error
        config = {'default': (), 'fr': ('en',)}
        with override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=config):
            self.assertRaises(ImproperlyConfigured, lambda: imp.reload(mt_settings))
        imp.reload(mt_settings)

    def test_resolution_order(self):
        from modeltranslation.utils import resolution_order
        with reload_override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=self.test_fallback):
            self.assertEqual(('en', 'de'), resolution_order('en'))
            self.assertEqual(('de', 'en'), resolution_order('de'))
            # Overriding
            config = {'default': ()}
            self.assertEqual(('en',), resolution_order('en', config))
            self.assertEqual(('de', 'en'), resolution_order('de', config))
            # Uniqueness
            config = {'de': ('en', 'de')}
            self.assertEqual(('en', 'de'), resolution_order('en', config))
            self.assertEqual(('de', 'en'), resolution_order('de', config))

            # Default fallbacks are always used at the end
            # That's it: fallbacks specified for a language don't replace defaults,
            # but just are prepended
            config = {'default': ('en', 'de'), 'de': ()}
            self.assertEqual(('en', 'de'), resolution_order('en', config))
            self.assertEqual(('de', 'en'), resolution_order('de', config))
            # What one may have expected
            self.assertNotEqual(('de',), resolution_order('de', config))

            # To completely override settings, one should override all keys
            config = {'default': (), 'de': ()}
            self.assertEqual(('en',), resolution_order('en', config))
            self.assertEqual(('de',), resolution_order('de', config))

    def test_fallback_languages(self):
        with reload_override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=self.test_fallback):
            title_de = 'title de'
            title_en = 'title en'
            n = models.TestModel(title=title_de)
            self.assertEqual(n.title_de, title_de)
            self.assertEqual(n.title_en, None)
            self.assertEqual(n.title, title_de)
            trans_real.activate('en')
            self.assertEqual(n.title, title_de)  # since default fallback is de

            n = models.TestModel(title=title_en)
            self.assertEqual(n.title_de, None)
            self.assertEqual(n.title_en, title_en)
            self.assertEqual(n.title, title_en)
            trans_real.activate('de')
            self.assertEqual(n.title, title_en)  # since fallback for de is en

            n.title_en = None
            self.assertEqual(n.title, '')  # if all fallbacks fail, return field.get_default()

    def test_fallbacks_toggle(self):
        with reload_override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=self.test_fallback):
            m = models.TestModel(title='foo')
            with fallbacks(True):
                self.assertEqual(m.title_de, 'foo')
                self.assertEqual(m.title_en, None)
                self.assertEqual(m.title, 'foo')
                with override('en'):
                    self.assertEqual(m.title, 'foo')
            with fallbacks(False):
                self.assertEqual(m.title_de, 'foo')
                self.assertEqual(m.title_en, None)
                self.assertEqual(m.title, 'foo')
                with override('en'):
                    self.assertEqual(m.title, '')  # '' is the default


class FileFieldsTest(ModeltranslationTestBase):

    def tearDown(self):
        if default_storage.exists('modeltranslation_tests'):
            # With FileSystemStorage uploading files creates a new directory,
            # that's not automatically removed upon their deletion.
            tests_dir = default_storage.path('modeltranslation_tests')
            if os.path.isdir(tests_dir):
                shutil.rmtree(tests_dir)
        super(FileFieldsTest, self).tearDown()

    def test_translated_models(self):
        field_names = dir(models.FileFieldsModel())
        self.assertTrue('id' in field_names)
        self.assertTrue('title' in field_names)
        self.assertTrue('title_de' in field_names)
        self.assertTrue('title_en' in field_names)
        self.assertTrue('file' in field_names)
        self.assertTrue('file_de' in field_names)
        self.assertTrue('file_en' in field_names)
        self.assertTrue('image' in field_names)
        self.assertTrue('image_de' in field_names)
        self.assertTrue('image_en' in field_names)

    def _file_factory(self, name, content):
        try:
            return ContentFile(content, name=name)
        except TypeError:  # In Django 1.3 ContentFile had no name parameter
            file = ContentFile(content)
            file.name = name
            return file

    def test_translated_models_instance(self):
        inst = models.FileFieldsModel(title="Testtitle")

        trans_real.activate("en")
        inst.title = 'title_en'
        inst.file = 'a_en'
        inst.file.save('b_en', ContentFile('file in english'))
        inst.image = self._file_factory('i_en.jpg', 'image in english')  # Direct assign

        trans_real.activate("de")
        inst.title = 'title_de'
        inst.file = 'a_de'
        inst.file.save('b_de', ContentFile('file in german'))
        inst.image = self._file_factory('i_de.jpg', 'image in german')

        inst.save()

        trans_real.activate("en")
        self.assertEqual(inst.title, 'title_en')
        self.assertTrue(inst.file.name.count('b_en') > 0)
        self.assertEqual(inst.file.read(), b'file in english')
        self.assertTrue(inst.image.name.count('i_en') > 0)
        self.assertEqual(inst.image.read(), b'image in english')

        # Check if file was actually created in the global storage.
        self.assertTrue(default_storage.exists(inst.file))
        self.assertTrue(inst.file.size > 0)
        self.assertTrue(default_storage.exists(inst.image))
        self.assertTrue(inst.image.size > 0)

        trans_real.activate("de")
        self.assertEqual(inst.title, 'title_de')
        self.assertTrue(inst.file.name.count('b_de') > 0)
        self.assertEqual(inst.file.read(), b'file in german')
        self.assertTrue(inst.image.name.count('i_de') > 0)
        self.assertEqual(inst.image.read(), b'image in german')

        inst.file_en.delete()
        inst.image_en.delete()
        inst.file_de.delete()
        inst.image_de.delete()


class ForeignKeyFieldsTest(ModeltranslationTestBase):

    def test_translated_models(self):
        field_names = dir(models.ForeignKeyModel())
        self.assertTrue('id' in field_names)
        for f in ('test', 'test_de', 'test_en', 'optional', 'optional_en', 'optional_de'):
            self.assertTrue(f in field_names)
            self.assertTrue('%s_id' % f in field_names)

    def test_db_column_names(self):
        meta = models.ForeignKeyModel._meta

        # Make sure the correct database columns always get used:
        attname, col = meta.get_field('test').get_attname_column()
        self.assertEqual(attname, 'test_id')
        self.assertEqual(attname, col)

        attname, col = meta.get_field('test_en').get_attname_column()
        self.assertEqual(attname, 'test_en_id')
        self.assertEqual(attname, col)

        attname, col = meta.get_field('test_de').get_attname_column()
        self.assertEqual(attname, 'test_de_id')
        self.assertEqual(attname, col)

    def test_translated_models_instance(self):
        test_inst1 = models.TestModel(title_en='title1_en', title_de='title1_de')
        test_inst1.save()
        test_inst2 = models.TestModel(title_en='title2_en', title_de='title2_de')
        test_inst2.save()
        inst = models.ForeignKeyModel()

        trans_real.activate("de")
        inst.test = test_inst1
        inst.optional = None

        trans_real.activate("en")
        # Test assigning relation by ID:
        inst.optional_id = test_inst2.pk
        inst.save()

        trans_real.activate("de")
        self.assertEqual(inst.test_id, test_inst1.pk)
        self.assertEqual(inst.test.title, 'title1_de')
        self.assertEqual(inst.test_de_id, test_inst1.pk)
        self.assertEqual(inst.test_de.title, 'title1_de')
        self.assertEqual(inst.optional, None)

        # Test fallbacks:
        trans_real.activate("en")
        with default_fallback():
            self.assertEqual(inst.test_id, test_inst1.pk)
            self.assertEqual(inst.test.pk, test_inst1.pk)
            self.assertEqual(inst.test.title, 'title1_en')

        # Test English:
        self.assertEqual(inst.optional_id, test_inst2.pk)
        self.assertEqual(inst.optional.title, 'title2_en')
        self.assertEqual(inst.optional_en_id, test_inst2.pk)
        self.assertEqual(inst.optional_en.title, 'title2_en')

        # Check filtering in direct way + lookup spanning
        inst.test_en = test_inst2
        inst.save()
        manager = models.ForeignKeyModel.objects

        trans_real.activate("de")
        self.assertEqual(manager.filter(test=test_inst1).count(), 1)
        self.assertEqual(manager.filter(test_en=test_inst1).count(), 0)
        self.assertEqual(manager.filter(test_de=test_inst1).count(), 1)
        self.assertEqual(manager.filter(test=test_inst2).count(), 0)
        self.assertEqual(manager.filter(test_en=test_inst2).count(), 1)
        self.assertEqual(manager.filter(test_de=test_inst2).count(), 0)
        self.assertEqual(manager.filter(test__title='title1_de').count(), 1)
        self.assertEqual(manager.filter(test__title='title1_en').count(), 0)
        self.assertEqual(manager.filter(test__title_en='title1_en').count(), 1)
        trans_real.activate("en")
        self.assertEqual(manager.filter(test=test_inst1).count(), 0)
        self.assertEqual(manager.filter(test_en=test_inst1).count(), 0)
        self.assertEqual(manager.filter(test_de=test_inst1).count(), 1)
        self.assertEqual(manager.filter(test=test_inst2).count(), 1)
        self.assertEqual(manager.filter(test_en=test_inst2).count(), 1)
        self.assertEqual(manager.filter(test_de=test_inst2).count(), 0)
        self.assertEqual(manager.filter(test__title='title2_en').count(), 1)
        self.assertEqual(manager.filter(test__title='title2_de').count(), 0)
        self.assertEqual(manager.filter(test__title_de='title2_de').count(), 1)

    def test_reverse_relations(self):
        test_inst = models.TestModel(title_en='title_en', title_de='title_de')
        test_inst.save()

        # Instantiate many 'ForeignKeyModel' instances:
        fk_inst_both = models.ForeignKeyModel(title_en='f_title_en', title_de='f_title_de',
                                              test_de=test_inst, test_en=test_inst)
        fk_inst_both.save()
        fk_inst_de = models.ForeignKeyModel(title_en='f_title_en', title_de='f_title_de',
                                            test_de_id=test_inst.pk)
        fk_inst_de.save()
        fk_inst_en = models.ForeignKeyModel(title_en='f_title_en', title_de='f_title_de',
                                            test_en=test_inst)
        fk_inst_en.save()

        fk_option_de = models.ForeignKeyModel.objects.create(optional_de=test_inst)
        fk_option_en = models.ForeignKeyModel.objects.create(optional_en=test_inst)

        # Check that the reverse accessors are created on the model:
        # Explicit related_name
        testmodel_fields = models.TestModel._meta.get_all_field_names()
        testmodel_methods = dir(models.TestModel)
        self.assertIn('test_fks',    testmodel_fields)
        self.assertIn('test_fks_de', testmodel_fields)
        self.assertIn('test_fks_en', testmodel_fields)
        self.assertIn('test_fks',    testmodel_methods)
        self.assertIn('test_fks_de', testmodel_methods)
        self.assertIn('test_fks_en', testmodel_methods)
        # Implicit related_name: manager descriptor name != query field name
        self.assertIn('foreignkeymodel',    testmodel_fields)
        self.assertIn('foreignkeymodel_de', testmodel_fields)
        self.assertIn('foreignkeymodel_en', testmodel_fields)
        self.assertIn('foreignkeymodel_set',    testmodel_methods)
        self.assertIn('foreignkeymodel_set_de', testmodel_methods)
        self.assertIn('foreignkeymodel_set_en', testmodel_methods)

        # Check the German reverse accessor:
        self.assertIn(fk_inst_both, test_inst.test_fks_de.all())
        self.assertIn(fk_inst_de, test_inst.test_fks_de.all())
        self.assertNotIn(fk_inst_en, test_inst.test_fks_de.all())

        # Check the English reverse accessor:
        self.assertIn(fk_inst_both, test_inst.test_fks_en.all())
        self.assertIn(fk_inst_en, test_inst.test_fks_en.all())
        self.assertNotIn(fk_inst_de, test_inst.test_fks_en.all())

        # Check the default reverse accessor:
        trans_real.activate("de")
        self.assertIn(fk_inst_de,    test_inst.test_fks.all())
        self.assertNotIn(fk_inst_en, test_inst.test_fks.all())
        trans_real.activate("en")
        self.assertIn(fk_inst_en,    test_inst.test_fks.all())
        self.assertNotIn(fk_inst_de, test_inst.test_fks.all())

        # Check implicit related_name reverse accessor:
        self.assertIn(fk_option_en, test_inst.foreignkeymodel_set.all())

        # Check filtering in reverse way + lookup spanning:
        manager = models.TestModel.objects
        trans_real.activate("de")
        self.assertEqual(manager.filter(test_fks=fk_inst_both).count(), 1)
        self.assertEqual(manager.filter(test_fks=fk_inst_de).count(), 1)
        self.assertEqual(manager.filter(test_fks__id=fk_inst_de.pk).count(), 1)
        self.assertEqual(manager.filter(test_fks=fk_inst_en).count(), 0)
        self.assertEqual(manager.filter(test_fks_en=fk_inst_en).count(), 1)
        self.assertEqual(manager.filter(foreignkeymodel=fk_option_de).count(), 1)
        self.assertEqual(manager.filter(foreignkeymodel=fk_option_en).count(), 0)
        self.assertEqual(manager.filter(foreignkeymodel_en=fk_option_en).count(), 1)
        self.assertEqual(manager.filter(test_fks__title='f_title_de').distinct().count(), 1)
        self.assertEqual(manager.filter(test_fks__title='f_title_en').distinct().count(), 0)
        self.assertEqual(manager.filter(test_fks__title_en='f_title_en').distinct().count(), 1)
        trans_real.activate("en")
        self.assertEqual(manager.filter(test_fks=fk_inst_both).count(), 1)
        self.assertEqual(manager.filter(test_fks=fk_inst_en).count(), 1)
        self.assertEqual(manager.filter(test_fks__id=fk_inst_en.pk).count(), 1)
        self.assertEqual(manager.filter(test_fks=fk_inst_de).count(), 0)
        self.assertEqual(manager.filter(test_fks_de=fk_inst_de).count(), 1)
        self.assertEqual(manager.filter(foreignkeymodel=fk_option_en).count(), 1)
        self.assertEqual(manager.filter(foreignkeymodel=fk_option_de).count(), 0)
        self.assertEqual(manager.filter(foreignkeymodel_de=fk_option_de).count(), 1)
        self.assertEqual(manager.filter(test_fks__title='f_title_en').distinct().count(), 1)
        self.assertEqual(manager.filter(test_fks__title='f_title_de').distinct().count(), 0)
        self.assertEqual(manager.filter(test_fks__title_de='f_title_de').distinct().count(), 1)

        # Check assignment
        trans_real.activate("de")
        test_inst2 = models.TestModel(title_en='title_en', title_de='title_de')
        test_inst2.save()
        test_inst2.test_fks = [fk_inst_de, fk_inst_both]
        test_inst2.test_fks_en = (fk_inst_en, fk_inst_both)

        self.assertEqual(fk_inst_both.test.pk, test_inst2.pk)
        self.assertEqual(fk_inst_both.test_id, test_inst2.pk)
        self.assertEqual(fk_inst_both.test_de, test_inst2)
        self.assertQuerysetsEqual(test_inst2.test_fks_de.all(), test_inst2.test_fks.all())
        self.assertIn(fk_inst_both, test_inst2.test_fks.all())
        self.assertIn(fk_inst_de, test_inst2.test_fks.all())
        self.assertNotIn(fk_inst_en, test_inst2.test_fks.all())
        trans_real.activate("en")
        self.assertQuerysetsEqual(test_inst2.test_fks_en.all(), test_inst2.test_fks.all())
        self.assertIn(fk_inst_both, test_inst2.test_fks.all())
        self.assertIn(fk_inst_en, test_inst2.test_fks.all())
        self.assertNotIn(fk_inst_de, test_inst2.test_fks.all())

    def test_non_translated_relation(self):
        non_de = models.NonTranslated.objects.create(title='title_de')
        non_en = models.NonTranslated.objects.create(title='title_en')

        fk_inst_both = models.ForeignKeyModel.objects.create(
            title_en='f_title_en', title_de='f_title_de', non_de=non_de, non_en=non_en)
        fk_inst_de = models.ForeignKeyModel.objects.create(non_de=non_de)
        fk_inst_en = models.ForeignKeyModel.objects.create(non_en=non_en)

        # Forward relation + spanning
        manager = models.ForeignKeyModel.objects
        trans_real.activate("de")
        self.assertEqual(manager.filter(non=non_de).count(), 2)
        self.assertEqual(manager.filter(non=non_en).count(), 0)
        self.assertEqual(manager.filter(non_en=non_en).count(), 2)
        self.assertEqual(manager.filter(non__title='title_de').count(), 2)
        self.assertEqual(manager.filter(non__title='title_en').count(), 0)
        self.assertEqual(manager.filter(non_en__title='title_en').count(), 2)
        trans_real.activate("en")
        self.assertEqual(manager.filter(non=non_en).count(), 2)
        self.assertEqual(manager.filter(non=non_de).count(), 0)
        self.assertEqual(manager.filter(non_de=non_de).count(), 2)
        self.assertEqual(manager.filter(non__title='title_en').count(), 2)
        self.assertEqual(manager.filter(non__title='title_de').count(), 0)
        self.assertEqual(manager.filter(non_de__title='title_de').count(), 2)

        # Reverse relation + spanning
        manager = models.NonTranslated.objects
        trans_real.activate("de")
        self.assertEqual(manager.filter(test_fks=fk_inst_both).count(), 1)
        self.assertEqual(manager.filter(test_fks=fk_inst_de).count(), 1)
        self.assertEqual(manager.filter(test_fks=fk_inst_en).count(), 0)
        self.assertEqual(manager.filter(test_fks_en=fk_inst_en).count(), 1)
        self.assertEqual(manager.filter(test_fks__title='f_title_de').count(), 1)
        self.assertEqual(manager.filter(test_fks__title='f_title_en').count(), 0)
        self.assertEqual(manager.filter(test_fks__title_en='f_title_en').count(), 1)
        trans_real.activate("en")
        self.assertEqual(manager.filter(test_fks=fk_inst_both).count(), 1)
        self.assertEqual(manager.filter(test_fks=fk_inst_en).count(), 1)
        self.assertEqual(manager.filter(test_fks=fk_inst_de).count(), 0)
        self.assertEqual(manager.filter(test_fks_de=fk_inst_de).count(), 1)
        self.assertEqual(manager.filter(test_fks__title='f_title_en').count(), 1)
        self.assertEqual(manager.filter(test_fks__title='f_title_de').count(), 0)
        self.assertEqual(manager.filter(test_fks__title_de='f_title_de').count(), 1)

    def assertQuerysetsEqual(self, qs1, qs2):
        pk = lambda o: o.pk
        return self.assertEqual(sorted(qs1, key=pk), sorted(qs2, key=pk))


class OtherFieldsTest(ModeltranslationTestBase):
    def test_translated_models(self):
        inst = models.OtherFieldsModel.objects.create()
        field_names = dir(inst)
        self.assertTrue('id' in field_names)
        self.assertTrue('int' in field_names)
        self.assertTrue('int_de' in field_names)
        self.assertTrue('int_en' in field_names)
        self.assertTrue('boolean' in field_names)
        self.assertTrue('boolean_de' in field_names)
        self.assertTrue('boolean_en' in field_names)
        self.assertTrue('nullboolean' in field_names)
        self.assertTrue('nullboolean_de' in field_names)
        self.assertTrue('nullboolean_en' in field_names)
        self.assertTrue('csi' in field_names)
        self.assertTrue('csi_de' in field_names)
        self.assertTrue('csi_en' in field_names)
        self.assertTrue('ip' in field_names)
        self.assertTrue('ip_de' in field_names)
        self.assertTrue('ip_en' in field_names)
#        self.assertTrue('genericip' in field_names)
#        self.assertTrue('genericip_de' in field_names)
#        self.assertTrue('genericip_en' in field_names)
        self.assertTrue('float' in field_names)
        self.assertTrue('float_de' in field_names)
        self.assertTrue('float_en' in field_names)
        self.assertTrue('decimal' in field_names)
        self.assertTrue('decimal_de' in field_names)
        self.assertTrue('decimal_en' in field_names)
        inst.delete()

    def test_translated_models_integer_instance(self):
        inst = models.OtherFieldsModel()
        inst.int = 7
        self.assertEqual('de', get_language())
        self.assertEqual(7, inst.int)
        self.assertEqual(7, inst.int_de)
        self.assertEqual(42, inst.int_en)  # default value is honored

        inst.int += 2
        inst.save()
        self.assertEqual(9, inst.int)
        self.assertEqual(9, inst.int_de)
        self.assertEqual(42, inst.int_en)

        trans_real.activate('en')
        inst.int -= 1
        self.assertEqual(41, inst.int)
        self.assertEqual(9, inst.int_de)
        self.assertEqual(41, inst.int_en)

        # this field has validator - let's try to make it below 0!
        inst.int -= 50
        self.assertRaises(ValidationError, inst.full_clean)

    def test_translated_models_boolean_instance(self):
        inst = models.OtherFieldsModel()
        inst.boolean = True
        self.assertEqual('de', get_language())
        self.assertEqual(True, inst.boolean)
        self.assertEqual(True, inst.boolean_de)
        self.assertEqual(False, inst.boolean_en)

        inst.boolean = False
        inst.save()
        self.assertEqual(False, inst.boolean)
        self.assertEqual(False, inst.boolean_de)
        self.assertEqual(False, inst.boolean_en)

        trans_real.activate('en')
        inst.boolean = True
        self.assertEqual(True, inst.boolean)
        self.assertEqual(False, inst.boolean_de)
        self.assertEqual(True, inst.boolean_en)

    def test_translated_models_nullboolean_instance(self):
        inst = models.OtherFieldsModel()
        inst.nullboolean = True
        self.assertEqual('de', get_language())
        self.assertEqual(True, inst.nullboolean)
        self.assertEqual(True, inst.nullboolean_de)
        self.assertEqual(None, inst.nullboolean_en)

        inst.nullboolean = False
        inst.save()
        self.assertEqual(False, inst.nullboolean)
        self.assertEqual(False, inst.nullboolean_de)
        self.assertEqual(None, inst.nullboolean_en)

        trans_real.activate('en')
        inst.nullboolean = True
        self.assertEqual(True, inst.nullboolean)
        self.assertEqual(False, inst.nullboolean_de)
        self.assertEqual(True, inst.nullboolean_en)

        inst.nullboolean = None
        self.assertEqual(None, inst.nullboolean)
        self.assertEqual(False, inst.nullboolean_de)
        self.assertEqual(None, inst.nullboolean_en)

    def test_translated_models_commaseparatedinteger_instance(self):
        inst = models.OtherFieldsModel()
        inst.csi = '4,8,15,16,23,42'
        self.assertEqual('de', get_language())
        self.assertEqual('4,8,15,16,23,42', inst.csi)
        self.assertEqual('4,8,15,16,23,42', inst.csi_de)
        self.assertEqual(None, inst.csi_en)

        inst.csi = '23,42'
        inst.save()
        self.assertEqual('23,42', inst.csi)
        self.assertEqual('23,42', inst.csi_de)
        self.assertEqual(None, inst.csi_en)

        trans_real.activate('en')
        inst.csi = '4,8,15,16,23,42'
        self.assertEqual('4,8,15,16,23,42', inst.csi)
        self.assertEqual('23,42', inst.csi_de)
        self.assertEqual('4,8,15,16,23,42', inst.csi_en)

        # Now that we have covered csi, lost, illuminati and hitchhiker
        # compliance in a single test, do something useful...

        # Check if validation is preserved
        inst.csi = '1;2'
        self.assertRaises(ValidationError, inst.full_clean)

    def test_translated_models_ipaddress_instance(self):
        inst = models.OtherFieldsModel()
        inst.ip = '192.0.1.42'
        self.assertEqual('de', get_language())
        self.assertEqual('192.0.1.42', inst.ip)
        self.assertEqual('192.0.1.42', inst.ip_de)
        self.assertEqual(None, inst.ip_en)

        inst.ip = '192.0.23.1'
        inst.save()
        self.assertEqual('192.0.23.1', inst.ip)
        self.assertEqual('192.0.23.1', inst.ip_de)
        self.assertEqual(None, inst.ip_en)

        trans_real.activate('en')
        inst.ip = '192.0.1.42'
        self.assertEqual('192.0.1.42', inst.ip)
        self.assertEqual('192.0.23.1', inst.ip_de)
        self.assertEqual('192.0.1.42', inst.ip_en)

        # Check if validation is preserved
        inst.ip = '1;2'
        self.assertRaises(ValidationError, inst.full_clean)

#    def test_translated_models_genericipaddress_instance(self):
#        inst = OtherFieldsModel()
#        inst.genericip = '2a02:42fe::4'
#        self.assertEqual('de', get_language())
#        self.assertEqual('2a02:42fe::4', inst.genericip)
#        self.assertEqual('2a02:42fe::4', inst.genericip_de)
#        self.assertEqual(None, inst.genericip_en)
#
#        inst.genericip = '2a02:23fe::4'
#        inst.save()
#        self.assertEqual('2a02:23fe::4', inst.genericip)
#        self.assertEqual('2a02:23fe::4', inst.genericip_de)
#        self.assertEqual(None, inst.genericip_en)
#
#        trans_real.activate('en')
#        inst.genericip = '2a02:42fe::4'
#        self.assertEqual('2a02:42fe::4', inst.genericip)
#        self.assertEqual('2a02:23fe::4', inst.genericip_de)
#        self.assertEqual('2a02:42fe::4', inst.genericip_en)
#
#        # Check if validation is preserved
#        inst.genericip = '1;2'
#        self.assertRaises(ValidationError, inst.full_clean)

    def test_translated_models_float_instance(self):
        inst = models.OtherFieldsModel()
        inst.float = 0.42
        self.assertEqual('de', get_language())
        self.assertEqual(0.42, inst.float)
        self.assertEqual(0.42, inst.float_de)
        self.assertEqual(None, inst.float_en)

        inst.float = 0.23
        inst.save()
        self.assertEqual(0.23, inst.float)
        self.assertEqual(0.23, inst.float_de)
        self.assertEqual(None, inst.float_en)

        inst.float += 0.08
        self.assertEqual(0.31, inst.float)
        self.assertEqual(0.31, inst.float_de)
        self.assertEqual(None, inst.float_en)

        trans_real.activate('en')
        inst.float = 0.42
        self.assertEqual(0.42, inst.float)
        self.assertEqual(0.31, inst.float_de)
        self.assertEqual(0.42, inst.float_en)

    def test_translated_models_decimal_instance(self):
        inst = models.OtherFieldsModel()
        inst.decimal = Decimal('0.42')
        self.assertEqual('de', get_language())
        self.assertEqual(Decimal('0.42'), inst.decimal)
        self.assertEqual(Decimal('0.42'), inst.decimal_de)
        self.assertEqual(None, inst.decimal_en)

        inst.decimal = inst.decimal - Decimal('0.19')
        inst.save()
        self.assertEqual(Decimal('0.23'), inst.decimal)
        self.assertEqual(Decimal('0.23'), inst.decimal_de)
        self.assertEqual(None, inst.decimal_en)

        trans_real.activate('en')
        self.assertRaises(TypeError, lambda x: inst.decimal + Decimal('0.19'))
        self.assertEqual(None, inst.decimal)
        self.assertEqual(Decimal('0.23'), inst.decimal_de)
        self.assertEqual(None, inst.decimal_en)

        inst.decimal = Decimal('0.42')
        self.assertEqual(Decimal('0.42'), inst.decimal)
        self.assertEqual(Decimal('0.23'), inst.decimal_de)
        self.assertEqual(Decimal('0.42'), inst.decimal_en)

    def test_translated_models_date_instance(self):
        inst = models.OtherFieldsModel()
        inst.date = datetime.date(2012, 12, 31)
        self.assertEqual('de', get_language())
        self.assertEqual(datetime.date(2012, 12, 31), inst.date)
        self.assertEqual(datetime.date(2012, 12, 31), inst.date_de)
        self.assertEqual(None, inst.date_en)

        inst.date = datetime.date(1999, 1, 1)
        inst.save()
        self.assertEqual(datetime.date(1999, 1, 1), inst.date)
        self.assertEqual(datetime.date(1999, 1, 1), inst.date_de)
        self.assertEqual(None, inst.date_en)

        qs = models.OtherFieldsModel.objects.filter(date='1999-1-1')
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].date, datetime.date(1999, 1, 1))

        trans_real.activate('en')
        inst.date = datetime.date(2012, 12, 31)
        self.assertEqual(datetime.date(2012, 12, 31), inst.date)
        self.assertEqual(datetime.date(1999, 1, 1), inst.date_de)
        self.assertEqual(datetime.date(2012, 12, 31), inst.date_en)

    def test_translated_models_datetime_instance(self):
        inst = models.OtherFieldsModel()
        inst.datetime = datetime.datetime(2012, 12, 31, 23, 42)
        self.assertEqual('de', get_language())
        self.assertEqual(datetime.datetime(2012, 12, 31, 23, 42), inst.datetime)
        self.assertEqual(datetime.datetime(2012, 12, 31, 23, 42), inst.datetime_de)
        self.assertEqual(None, inst.datetime_en)

        inst.datetime = datetime.datetime(1999, 1, 1, 23, 42)
        inst.save()
        self.assertEqual(datetime.datetime(1999, 1, 1, 23, 42), inst.datetime)
        self.assertEqual(datetime.datetime(1999, 1, 1, 23, 42), inst.datetime_de)
        self.assertEqual(None, inst.datetime_en)

        qs = models.OtherFieldsModel.objects.filter(datetime='1999-1-1 23:42')
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].datetime, datetime.datetime(1999, 1, 1, 23, 42))

        trans_real.activate('en')
        inst.datetime = datetime.datetime(2012, 12, 31, 23, 42)
        self.assertEqual(datetime.datetime(2012, 12, 31, 23, 42), inst.datetime)
        self.assertEqual(datetime.datetime(1999, 1, 1, 23, 42), inst.datetime_de)
        self.assertEqual(datetime.datetime(2012, 12, 31, 23, 42), inst.datetime_en)

    def test_translated_models_time_instance(self):
        inst = models.OtherFieldsModel()
        inst.time = datetime.time(23, 42, 0)
        self.assertEqual('de', get_language())
        self.assertEqual(datetime.time(23, 42, 0), inst.time)
        self.assertEqual(datetime.time(23, 42, 0), inst.time_de)
        self.assertEqual(None, inst.time_en)

        inst.time = datetime.time(1, 2, 3)
        inst.save()
        self.assertEqual(datetime.time(1, 2, 3), inst.time)
        self.assertEqual(datetime.time(1, 2, 3), inst.time_de)
        self.assertEqual(None, inst.time_en)

        qs = models.OtherFieldsModel.objects.filter(time='01:02:03')
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].time, datetime.time(1, 2, 3))

        trans_real.activate('en')
        inst.time = datetime.time(23, 42, 0)
        self.assertEqual(datetime.time(23, 42, 0), inst.time)
        self.assertEqual(datetime.time(1, 2, 3), inst.time_de)
        self.assertEqual(datetime.time(23, 42, 0), inst.time_en)

    def test_descriptors(self):
        # Descriptor store ints in database and returns string of 'a' of that length
        inst = models.DescriptorModel()
        # Demonstrate desired behaviour
        inst.normal = 2
        self.assertEqual('aa', inst.normal)
        inst.normal = 'abc'
        self.assertEqual('aaa', inst.normal)

        # Descriptor on translated field works too
        self.assertEqual('de', get_language())
        inst.trans = 5
        self.assertEqual('aaaaa', inst.trans)

        inst.save()
        db_values = models.DescriptorModel.objects.values('normal', 'trans_en', 'trans_de')[0]
        self.assertEqual(3, db_values['normal'])
        self.assertEqual(5, db_values['trans_de'])
        self.assertEqual(0, db_values['trans_en'])

        # Retrieval from db
        inst = models.DescriptorModel.objects.all()[0]
        self.assertEqual('aaa', inst.normal)
        self.assertEqual('aaaaa', inst.trans)
        self.assertEqual('aaaaa', inst.trans_de)
        self.assertEqual('', inst.trans_en)

        # Other language
        trans_real.activate('en')
        self.assertEqual('', inst.trans)
        inst.trans = 'q'
        self.assertEqual('a', inst.trans)
        inst.trans_de = 4
        self.assertEqual('aaaa', inst.trans_de)
        inst.save()
        db_values = models.DescriptorModel.objects.values('normal', 'trans_en', 'trans_de')[0]
        self.assertEqual(3, db_values['normal'])
        self.assertEqual(4, db_values['trans_de'])
        self.assertEqual(1, db_values['trans_en'])


class ModeltranslationTestRule1(ModeltranslationTestBase):
    """
    Rule 1: Reading the value from the original field returns the value in
    translated to the current language.
    """
    def _test_field(self, field_name, value_de, value_en, deactivate=True):
        field_name_de = '%s_de' % field_name
        field_name_en = '%s_en' % field_name
        params = {field_name_de: value_de, field_name_en: value_en}

        n = models.TestModel.objects.create(**params)
        # Language is set to 'de' at this point
        self.assertEqual(get_language(), 'de')
        self.assertEqual(getattr(n, field_name), value_de)
        self.assertEqual(getattr(n, field_name_de), value_de)
        self.assertEqual(getattr(n, field_name_en), value_en)
        # Now switch to "en"
        trans_real.activate("en")
        self.assertEqual(get_language(), "en")
        # Should now be return the english one (just by switching the language)
        self.assertEqual(getattr(n, field_name), value_en)
        # But explicit language fields hold their values
        self.assertEqual(getattr(n, field_name_de), value_de)
        self.assertEqual(getattr(n, field_name_en), value_en)

        n = models.TestModel.objects.create(**params)
        n.save()
        # Language is set to "en" at this point
        self.assertEqual(get_language(), "en")
        self.assertEqual(getattr(n, field_name), value_en)
        self.assertEqual(getattr(n, field_name_de), value_de)
        self.assertEqual(getattr(n, field_name_en), value_en)
        trans_real.activate('de')
        self.assertEqual(get_language(), 'de')
        self.assertEqual(getattr(n, field_name), value_de)

        if deactivate:
            trans_real.deactivate()

    def test_rule1(self):
        """
        Basic CharField/TextField test.
        """
        title1_de = "title de"
        title1_en = "title en"
        text_de = "Dies ist ein deutscher Satz"
        text_en = "This is an english sentence"

        self._test_field(field_name='title', value_de=title1_de, value_en=title1_en)
        self._test_field(field_name='text', value_de=text_de, value_en=text_en)

    def test_rule1_url_field(self):
        self._test_field(field_name='url',
                         value_de='http://www.google.de',
                         value_en='http://www.google.com')

    def test_rule1_email_field(self):
        self._test_field(field_name='email',
                         value_de='django-modeltranslation@googlecode.de',
                         value_en='django-modeltranslation@googlecode.com')


class ModeltranslationTestRule2(ModeltranslationTestBase):
    """
    Rule 2: Assigning a value to the original field updates the value
    in the associated current language translation field.
    """
    def _test_field(self, field_name, value1_de, value1_en, value2, value3,
                    deactivate=True):
        field_name_de = '%s_de' % field_name
        field_name_en = '%s_en' % field_name
        params = {field_name_de: value1_de, field_name_en: value1_en}

        self.assertEqual(get_language(), 'de')
        n = models.TestModel.objects.create(**params)
        self.assertEqual(getattr(n, field_name), value1_de)
        self.assertEqual(getattr(n, field_name_de), value1_de)
        self.assertEqual(getattr(n, field_name_en), value1_en)

        setattr(n, field_name, value2)
        n.save()
        self.assertEqual(getattr(n, field_name), value2)
        self.assertEqual(getattr(n, field_name_de), value2)
        self.assertEqual(getattr(n, field_name_en), value1_en)

        trans_real.activate("en")
        self.assertEqual(get_language(), "en")

        setattr(n, field_name, value3)
        setattr(n, field_name_de, value1_de)
        n.save()
        self.assertEqual(getattr(n, field_name), value3)
        self.assertEqual(getattr(n, field_name_en), value3)
        self.assertEqual(getattr(n, field_name_de), value1_de)

        if deactivate:
            trans_real.deactivate()

    def test_rule2(self):
        """
        Basic CharField/TextField test.
        """
        self._test_field(field_name='title',
                         value1_de='title de',
                         value1_en='title en',
                         value2='Neuer Titel',
                         value3='new title')

    def test_rule2_url_field(self):
        self._test_field(field_name='url',
                         value1_de='http://www.google.de',
                         value1_en='http://www.google.com',
                         value2='http://www.google.at',
                         value3='http://www.google.co.uk')

    def test_rule2_email_field(self):
        self._test_field(field_name='email',
                         value1_de='django-modeltranslation@googlecode.de',
                         value1_en='django-modeltranslation@googlecode.com',
                         value2='django-modeltranslation@googlecode.at',
                         value3='django-modeltranslation@googlecode.co.uk')


class ModeltranslationTestRule3(ModeltranslationTestBase):
    """
    Rule 3: If both fields - the original and the current language translation
    field - are updated at the same time, the current language translation
    field wins.
    """

    def test_rule3(self):
        self.assertEqual(get_language(), 'de')
        title = 'title de'

        # Normal behaviour
        n = models.TestModel(title='foo')
        self.assertEqual(n.title, 'foo')
        self.assertEqual(n.title_de, 'foo')
        self.assertEqual(n.title_en, None)

        # constructor
        n = models.TestModel(title_de=title, title='foo')
        self.assertEqual(n.title, title)
        self.assertEqual(n.title_de, title)
        self.assertEqual(n.title_en, None)

        # object.create
        n = models.TestModel.objects.create(title_de=title, title='foo')
        self.assertEqual(n.title, title)
        self.assertEqual(n.title_de, title)
        self.assertEqual(n.title_en, None)

        # Database save/load
        n = models.TestModel.objects.get(title_de=title)
        self.assertEqual(n.title, title)
        self.assertEqual(n.title_de, title)
        self.assertEqual(n.title_en, None)

        # This is not subject to Rule 3, because updates are not *at the ame time*
        n = models.TestModel()
        n.title_de = title
        n.title = 'foo'
        self.assertEqual(n.title, 'foo')
        self.assertEqual(n.title_de, 'foo')
        self.assertEqual(n.title_en, None)

    @staticmethod
    def _index(list, element):
        for i, el in enumerate(list):
            if el is element:
                return i
        raise ValueError

    def test_rule3_internals(self):
        # Rule 3 work because translation fields are added to model field list
        # later than original field.
        original = models.TestModel._meta.get_field('title')
        translated_de = models.TestModel._meta.get_field('title_de')
        translated_en = models.TestModel._meta.get_field('title_en')
        fields = models.TestModel._meta.fields
        # Here we cannot use simple list.index, because Field has overloaded __cmp__
        self.assertTrue(self._index(fields, original) < self._index(fields, translated_de))
        self.assertTrue(self._index(fields, original) < self._index(fields, translated_en))


class ModelValidationTest(ModeltranslationTestBase):
    """
    Tests if a translation model field validates correctly.
    """
    def assertRaisesValidation(self, func):
        try:
            func()
        except ValidationError as e:
            return e.message_dict
        self.fail('ValidationError not raised.')

    def _test_model_validation(self, field_name, invalid_value, valid_value):
        """
        Generic model field validation test.
        """
        field_name_de = '%s_de' % field_name
        field_name_en = '%s_en' % field_name
        # Title need to be passed here - otherwise it would not validate
        params = {'title_de': 'title de', 'title_en': 'title en', field_name: invalid_value}

        n = models.TestModel.objects.create(**params)

        # First check the original field
        # Expect that the validation object contains an error
        errors = self.assertRaisesValidation(n.full_clean)
        self.assertIn(field_name, errors)

        # Set translation field to a valid value
        # Language is set to 'de' at this point
        self.assertEqual(get_language(), 'de')
        setattr(n, field_name_de, valid_value)
        n.full_clean()

        # All language fields are validated even though original field validation raise no error
        setattr(n, field_name_en, invalid_value)
        errors = self.assertRaisesValidation(n.full_clean)
        self.assertNotIn(field_name, errors)
        self.assertIn(field_name_en, errors)

        # When language is changed to en, the original field also doesn't validate
        with override('en'):
            setattr(n, field_name_en, invalid_value)
            errors = self.assertRaisesValidation(n.full_clean)
            self.assertIn(field_name, errors)
            self.assertIn(field_name_en, errors)

        # Set translation field to an invalid value
        setattr(n, field_name_en, valid_value)
        setattr(n, field_name_de, invalid_value)
        # Expect that the validation object contains an error for url_de
        errors = self.assertRaisesValidation(n.full_clean)
        self.assertIn(field_name, errors)
        self.assertIn(field_name_de, errors)

    def test_model_validation_required(self):
        """
        General test for CharField: if required/blank is handled properly.
        """
        # Create an object without title (which is required)
        n = models.TestModel.objects.create(text='Testtext')

        # First check the original field
        # Expect that the validation object contains an error for title
        errors = self.assertRaisesValidation(n.full_clean)
        self.assertIn('title', errors)
        n.save()

        # Check the translation field
        # Language is set to 'de' at this point
        self.assertEqual(get_language(), 'de')
        # Set translation field to a valid title
        n.title_de = 'Title'
        n.full_clean()

        # Change language to en
        # Now validation fails, because current language (en) title is empty
        # So requirement validation depends on current language
        with override('en'):
            errors = self.assertRaisesValidation(n.full_clean)
            self.assertIn('title', errors)

            # However, with fallback language (most cases), it validates (because empty title
            # falls back to title_de):
            with default_fallback():
                n.full_clean()

        # Set translation field to an empty title
        n.title_de = None
        # Even though the original field isn't optional, translation fields are
        # per definition always optional. So we expect that the validation
        # object contains no error for title_de.
        # However, title still raises error, since it points to empty title_de
        errors = self.assertRaisesValidation(n.full_clean)
        self.assertNotIn('title_de', errors)
        self.assertIn('title', errors)

    def test_model_validation_url_field(self):
        self._test_model_validation(
            field_name='url',
            invalid_value='foo en',
            valid_value='http://code.google.com/p/django-modeltranslation/')

    def test_model_validation_email_field(self):
        self._test_model_validation(
            field_name='email', invalid_value='foo en',
            valid_value='django-modeltranslation@googlecode.com')


class ModelInheritanceTest(ModeltranslationTestBase):
    """Tests for inheritance support in modeltranslation."""
    def test_abstract_inheritance(self):
        field_names_b = models.AbstractModelB._meta.get_all_field_names()
        self.assertFalse('titled' in field_names_b)
        self.assertFalse('titled_de' in field_names_b)
        self.assertFalse('titled_en' in field_names_b)

    def test_multitable_inheritance(self):
        field_names_a = models.MultitableModelA._meta.get_all_field_names()
        self.assertTrue('titlea' in field_names_a)
        self.assertTrue('titlea_de' in field_names_a)
        self.assertTrue('titlea_en' in field_names_a)

        field_names_b = models.MultitableModelB._meta.get_all_field_names()
        self.assertTrue('titlea' in field_names_b)
        self.assertTrue('titlea_de' in field_names_b)
        self.assertTrue('titlea_en' in field_names_b)
        self.assertTrue('titleb' in field_names_b)
        self.assertTrue('titleb_de' in field_names_b)
        self.assertTrue('titleb_en' in field_names_b)

        field_names_c = models.MultitableModelC._meta.get_all_field_names()
        self.assertTrue('titlea' in field_names_c)
        self.assertTrue('titlea_de' in field_names_c)
        self.assertTrue('titlea_en' in field_names_c)
        self.assertTrue('titleb' in field_names_c)
        self.assertTrue('titleb_de' in field_names_c)
        self.assertTrue('titleb_en' in field_names_c)
        self.assertTrue('titlec' in field_names_c)
        self.assertTrue('titlec_de' in field_names_c)
        self.assertTrue('titlec_en' in field_names_c)

        field_names_d = models.MultitableModelD._meta.get_all_field_names()
        self.assertTrue('titlea' in field_names_d)
        self.assertTrue('titlea_de' in field_names_d)
        self.assertTrue('titlea_en' in field_names_d)
        self.assertTrue('titleb' in field_names_d)
        self.assertTrue('titleb_de' in field_names_d)
        self.assertTrue('titleb_en' in field_names_d)
        self.assertTrue('titled' in field_names_d)

    def test_inheritance(self):
        def assertLocalFields(model, local_fields):
            # Proper fields are inherited.
            opts = translator.translator.get_options_for_model(model)
            self.assertEqual(set(opts.local_fields.keys()), set(local_fields))
            # Local translation fields are created on the model.
            model_local_fields = [f.name for f in model._meta.local_fields]
            for field in local_fields:
                for lang in mt_settings.AVAILABLE_LANGUAGES:
                    translation_field = build_localized_fieldname(field, lang)
                    self.assertTrue(translation_field in model_local_fields)

        def assertFields(model, fields):
            # The given fields are inherited.
            opts = translator.translator.get_options_for_model(model)
            self.assertEqual(set(opts.fields.keys()), set(fields))
            # Inherited translation fields are available on the model.
            model_fields = model._meta.get_all_field_names()
            for field in fields:
                for lang in mt_settings.AVAILABLE_LANGUAGES:
                    translation_field = build_localized_fieldname(field, lang)
                    self.assertTrue(translation_field in model_fields)

        # Translation fields can be declared on abstract classes.
        assertLocalFields(models.Slugged, ('slug',))
        assertLocalFields(models.MetaData, ('keywords',))
        assertLocalFields(models.RichText, ('content',))
        # Local fields are inherited from abstract superclasses.
        assertLocalFields(models.Displayable, ('slug', 'keywords',))
        assertLocalFields(models.Page, ('slug', 'keywords', 'title',))
        # But not from concrete superclasses.
        assertLocalFields(models.RichTextPage, ('content',))

        # Fields inherited from concrete models are also available.
        assertFields(models.Slugged, ('slug',))
        assertFields(models.Page, ('slug', 'keywords', 'title',))
        assertFields(models.RichTextPage, ('slug', 'keywords', 'title',
                                           'content',))


class ModelInheritanceFieldAggregationTest(ModeltranslationTestBase):
    """
    Tests for inheritance support with field aggregation
    in modeltranslation.
    """
    def test_field_aggregation(self):
        clsb = FieldInheritanceCTranslationOptions
        self.assertTrue('titlea' in clsb.fields)
        self.assertTrue('titleb' in clsb.fields)
        self.assertTrue('titlec' in clsb.fields)
        self.assertEqual(3, len(clsb.fields))
        self.assertEqual(tuple, type(clsb.fields))

    def test_multi_inheritance(self):
        clsb = FieldInheritanceETranslationOptions
        self.assertTrue('titlea' in clsb.fields)
        self.assertTrue('titleb' in clsb.fields)
        self.assertTrue('titlec' in clsb.fields)
        self.assertTrue('titled' in clsb.fields)
        self.assertTrue('titlee' in clsb.fields)
        self.assertEqual(5, len(clsb.fields))  # there are no repetitions


class UpdateCommandTest(ModeltranslationTestBase):
    def test_update_command(self):
        # Here it would be convenient to use fixtures - unfortunately,
        # fixtures loader doesn't use raw sql but rather creates objects,
        # so translation descriptor affects result and we cannot set the
        # 'original' field value.
        pk1 = models.TestModel.objects.create(title_de='').pk
        pk2 = models.TestModel.objects.create(title_de='already').pk
        # Due to ``rewrite(False)`` here, original field will be affected.
        models.TestModel.objects.all().rewrite(False).update(title='initial')

        # Check raw data using ``values``
        obj1 = models.TestModel.objects.filter(pk=pk1).values()[0]
        obj2 = models.TestModel.objects.filter(pk=pk2).values()[0]
        self.assertEqual('', obj1['title_de'])
        self.assertEqual('initial', obj1['title'])
        self.assertEqual('already', obj2['title_de'])
        self.assertEqual('initial', obj2['title'])

        call_command('update_translation_fields', verbosity=0)

        obj1 = models.TestModel.objects.get(pk=pk1)
        obj2 = models.TestModel.objects.get(pk=pk2)
        self.assertEqual('initial', obj1.title_de)
        self.assertEqual('already', obj2.title_de)


class TranslationAdminTest(ModeltranslationTestBase):
    def setUp(self):
        super(TranslationAdminTest, self).setUp()
        self.test_obj = models.TestModel.objects.create(
            title='Testtitle', text='Testtext')
        self.site = AdminSite()

    def tearDown(self):
        self.test_obj.delete()
        super(TranslationAdminTest, self).tearDown()

    def test_default_fields(self):
        class TestModelAdmin(admin.TranslationAdmin):
            pass

        ma = TestModelAdmin(models.TestModel, self.site)
        self.assertEqual(
            tuple(ma.get_form(request).base_fields.keys()),
            ('title_de', 'title_en', 'text_de', 'text_en', 'url_de', 'url_en',
             'email_de', 'email_en'))

    def test_default_fieldsets(self):
        class TestModelAdmin(admin.TranslationAdmin):
            pass

        ma = TestModelAdmin(models.TestModel, self.site)
        # We expect that the original field is excluded and only the
        # translation fields are included in fields
        fields = ['title_de', 'title_en', 'text_de', 'text_en',
                  'url_de', 'url_en', 'email_de', 'email_en']
        self.assertEqual(
            ma.get_fieldsets(request), [(None, {'fields': fields})])
        self.assertEqual(
            ma.get_fieldsets(request, self.test_obj),
            [(None, {'fields': fields})])

    def test_field_arguments(self):
        class TestModelAdmin(admin.TranslationAdmin):
            fields = ['title']

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ['title_de', 'title_en']
        self.assertEqual(tuple(ma.get_form(request).base_fields.keys()), tuple(fields))
        self.assertEqual(
            tuple(ma.get_form(request, self.test_obj).base_fields.keys()), tuple(fields))

    def test_field_arguments_restricted_on_form(self):
        # Using `fields`.
        class TestModelAdmin(admin.TranslationAdmin):
            fields = ['title']

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ['title_de', 'title_en']
        self.assertEqual(tuple(ma.get_form(request).base_fields.keys()), tuple(fields))
        self.assertEqual(
            tuple(ma.get_form(request, self.test_obj).base_fields.keys()), tuple(fields))

        # Using `fieldsets`.
        class TestModelAdmin(admin.TranslationAdmin):
            fieldsets = [(None, {'fields': ['title']})]

        ma = TestModelAdmin(models.TestModel, self.site)
        self.assertEqual(tuple(ma.get_form(request).base_fields.keys()), tuple(fields))
        self.assertEqual(
            tuple(ma.get_form(request, self.test_obj).base_fields.keys()), tuple(fields))

        # Using `exclude`.
        class TestModelAdmin(admin.TranslationAdmin):
            exclude = ['url', 'email']

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ['title_de', 'title_en', 'text_de', 'text_en']
        self.assertEqual(
            tuple(ma.get_form(request).base_fields.keys()), tuple(fields))

        # You can also pass a tuple to `exclude`.
        class TestModelAdmin(admin.TranslationAdmin):
            exclude = ('url', 'email')

        ma = TestModelAdmin(models.TestModel, self.site)
        self.assertEqual(
            tuple(ma.get_form(request).base_fields.keys()), tuple(fields))
        self.assertEqual(
            tuple(ma.get_form(request, self.test_obj).base_fields.keys()), tuple(fields))

        # Using `fields` and `exclude`.
        class TestModelAdmin(admin.TranslationAdmin):
            fields = ['title', 'url']
            exclude = ['url']

        ma = TestModelAdmin(models.TestModel, self.site)
        self.assertEqual(
            tuple(ma.get_form(request).base_fields.keys()), ('title_de', 'title_en'))

        # Using `fields` and `readonly_fields`.
        class TestModelAdmin(admin.TranslationAdmin):
            fields = ['title', 'url']
            readonly_fields = ['url']

        ma = TestModelAdmin(models.TestModel, self.site)
        self.assertEqual(
            tuple(ma.get_form(request).base_fields.keys()), ('title_de', 'title_en'))

        # Using `readonly_fields`.
        # Note: readonly fields are not included in the form.
        class TestModelAdmin(admin.TranslationAdmin):
            readonly_fields = ['title']

        ma = TestModelAdmin(models.TestModel, self.site)
        self.assertEqual(
            tuple(ma.get_form(request).base_fields.keys()),
            ('text_de', 'text_en', 'url_de', 'url_en', 'email_de', 'email_en'))

        # Using grouped fields.
        # Note: Current implementation flattens the nested fields.
        class TestModelAdmin(admin.TranslationAdmin):
            fields = (('title', 'url'), 'email',)

        ma = TestModelAdmin(models.TestModel, self.site)
        self.assertEqual(
            tuple(ma.get_form(request).base_fields.keys()),
            ('title_de', 'title_en', 'url_de', 'url_en', 'email_de', 'email_en'))

        # Using grouped fields in `fieldsets`.
        class TestModelAdmin(admin.TranslationAdmin):
            fieldsets = [(None, {'fields': ('email', ('title', 'url'))})]

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ['email_de', 'email_en', 'title_de', 'title_en', 'url_de', 'url_en']
        self.assertEqual(tuple(ma.get_form(request).base_fields.keys()), tuple(fields))
        self.assertEqual(
            tuple(ma.get_form(request, self.test_obj).base_fields.keys()), tuple(fields))

    def test_field_arguments_restricted_on_custom_form(self):
        # Using `fields`.
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = models.TestModel
                fields = ['url', 'email']

        class TestModelAdmin(admin.TranslationAdmin):
            form = TestModelForm

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ['url_de', 'url_en', 'email_de', 'email_en']
        self.assertEqual(
            tuple(ma.get_form(request).base_fields.keys()), tuple(fields))
        self.assertEqual(
            tuple(ma.get_form(request, self.test_obj).base_fields.keys()), tuple(fields))

        # Using `exclude`.
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = models.TestModel
                exclude = ['url', 'email']

        class TestModelAdmin(admin.TranslationAdmin):
            form = TestModelForm

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ['title_de', 'title_en', 'text_de', 'text_en']
        self.assertEqual(
            tuple(ma.get_form(request).base_fields.keys()), tuple(fields))
        self.assertEqual(
            tuple(ma.get_form(request, self.test_obj).base_fields.keys()), tuple(fields))

        # If both, the custom form an the ModelAdmin define an `exclude`
        # option, the ModelAdmin wins. This is Django behaviour.
        class TestModelAdmin(admin.TranslationAdmin):
            form = TestModelForm
            exclude = ['url']

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ['title_de', 'title_en', 'text_de', 'text_en', 'email_de',
                  'email_en']
        self.assertEqual(
            tuple(ma.get_form(request).base_fields.keys()), tuple(fields))
        self.assertEqual(
            tuple(ma.get_form(request, self.test_obj).base_fields.keys()), tuple(fields))

        # Same for `fields`.
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = models.TestModel
                fields = ['text', 'title']

        class TestModelAdmin(admin.TranslationAdmin):
            form = TestModelForm
            fields = ['email']

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ['email_de', 'email_en']
        self.assertEqual(
            tuple(ma.get_form(request).base_fields.keys()), tuple(fields))
        self.assertEqual(
            tuple(ma.get_form(request, self.test_obj).base_fields.keys()), tuple(fields))

    def test_inline_fieldsets(self):
        class DataInline(admin.TranslationStackedInline):
            model = models.DataModel
            fieldsets = [
                ('Test', {'fields': ('data',)})
            ]

        class TestModelAdmin(admin.TranslationAdmin):
            exclude = ('title', 'text',)
            inlines = [DataInline]

        class DataTranslationOptions(translator.TranslationOptions):
            fields = ('data',)

        translator.translator.register(models.DataModel,
                                       DataTranslationOptions)
        ma = TestModelAdmin(models.TestModel, self.site)

        fieldsets = [('Test', {'fields': ['data_de', 'data_en']})]

        try:
            ma_fieldsets = ma.get_inline_instances(
                request)[0].get_fieldsets(request)
        except AttributeError:  # Django 1.3 fallback
            ma_fieldsets = ma.inlines[0](
                models.TestModel, self.site).get_fieldsets(request)
        self.assertEqual(ma_fieldsets, fieldsets)

        try:
            ma_fieldsets = ma.get_inline_instances(
                request)[0].get_fieldsets(request, self.test_obj)
        except AttributeError:  # Django 1.3 fallback
            ma_fieldsets = ma.inlines[0](
                models.TestModel, self.site).get_fieldsets(request, self.test_obj)
        self.assertEqual(ma_fieldsets, fieldsets)

        # Remove translation for DataModel
        translator.translator.unregister(models.DataModel)

    def test_build_css_class(self):
        with reload_override_settings(LANGUAGES=(('de', 'German'), ('en', 'English'),
                                                 ('es-ar', 'Argentinian Spanish'),)):
            fields = {
                'foo_en': 'foo-en',
                'foo_es_ar': 'foo-es_ar',
                'foo_en_us': 'foo-en_us',
                'foo_bar_de': 'foo_bar-de',
                '_foo_en': '_foo-en',
                '_foo_es_ar': '_foo-es_ar',
                '_foo_bar_de': '_foo_bar-de',
                'foo__en': 'foo_-en',
                'foo__es_ar': 'foo_-es_ar',
                'foo_bar__de': 'foo_bar_-de',
            }
            for field, css in fields.items():
                self.assertEqual(build_css_class(field), css)

    def test_multitable_inheritance(self):
        class MultitableModelAAdmin(admin.TranslationAdmin):
            pass

        class MultitableModelBAdmin(admin.TranslationAdmin):
            pass

        maa = MultitableModelAAdmin(models.MultitableModelA, self.site)
        mab = MultitableModelBAdmin(models.MultitableModelB, self.site)

        self.assertEqual(tuple(maa.get_form(request).base_fields.keys()),
                         ('titlea_de', 'titlea_en'))
        self.assertEqual(tuple(mab.get_form(request).base_fields.keys()),
                         ('titlea_de', 'titlea_en', 'titleb_de', 'titleb_en'))

    def test_group_fieldsets(self):
        # Declared fieldsets take precedence over group_fieldsets
        class GroupFieldsetsModelAdmin(admin.TranslationAdmin):
            fieldsets = [(None, {'fields': ['title']})]
            group_fieldsets = True
        ma = GroupFieldsetsModelAdmin(models.GroupFieldsetsModel, self.site)
        fields = ['title_de', 'title_en']
        self.assertEqual(tuple(ma.get_form(request).base_fields.keys()), tuple(fields))
        self.assertEqual(
            tuple(ma.get_form(request, self.test_obj).base_fields.keys()), tuple(fields))

        # Now set group_fieldsets only
        class GroupFieldsetsModelAdmin(admin.TranslationAdmin):
            group_fieldsets = True
        ma = GroupFieldsetsModelAdmin(models.GroupFieldsetsModel, self.site)
        # Only text and title are registered for translation. We expect to get
        # three fieldsets. The first which gathers all untranslated field
        # (email only) and one for each translation field (text and title).
        fieldsets = [
            ('', {'fields': ['email']}),
            ('text', {'classes': ('mt-fieldset',), 'fields': ['text_de', 'text_en']}),
            ('title', {'classes': ('mt-fieldset',), 'fields': ['title_de', 'title_en']})
        ]
        self.assertEqual(ma.get_fieldsets(request), fieldsets)
        self.assertEqual(ma.get_fieldsets(request, self.test_obj), fieldsets)

        # Verify that other options are still taken into account

        # Exclude an untranslated field
        class GroupFieldsetsModelAdmin(admin.TranslationAdmin):
            group_fieldsets = True
            exclude = ('email',)
        ma = GroupFieldsetsModelAdmin(models.GroupFieldsetsModel, self.site)
        fieldsets = [
            ('text', {'classes': ('mt-fieldset',), 'fields': ['text_de', 'text_en']}),
            ('title', {'classes': ('mt-fieldset',), 'fields': ['title_de', 'title_en']})
        ]
        self.assertEqual(ma.get_fieldsets(request), fieldsets)
        self.assertEqual(ma.get_fieldsets(request, self.test_obj), fieldsets)

        # Exclude a translation field
        class GroupFieldsetsModelAdmin(admin.TranslationAdmin):
            group_fieldsets = True
            exclude = ('text',)
        ma = GroupFieldsetsModelAdmin(models.GroupFieldsetsModel, self.site)
        fieldsets = [
            ('', {'fields': ['email']}),
            ('title', {'classes': ('mt-fieldset',), 'fields': ['title_de', 'title_en']})
        ]
        self.assertEqual(ma.get_fieldsets(request), fieldsets)
        self.assertEqual(ma.get_fieldsets(request, self.test_obj), fieldsets)

    def test_prepopulated_fields(self):
        trans_real.activate('de')
        self.assertEqual(get_language(), 'de')

        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {'slug': ('firstname',)}
        ma = NameModelAdmin(models.NameModel, self.site)
        self.assertEqual(ma.prepopulated_fields, {'slug': ('firstname_de',)})

        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {'slug': ('firstname', 'lastname',)}
        ma = NameModelAdmin(models.NameModel, self.site)
        self.assertEqual(ma.prepopulated_fields, {'slug': ('firstname_de', 'lastname_de',)})

        trans_real.activate('en')
        self.assertEqual(get_language(), 'en')

        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {'slug': ('firstname',)}
        ma = NameModelAdmin(models.NameModel, self.site)
        self.assertEqual(ma.prepopulated_fields, {'slug': ('firstname_en',)})

        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {'slug': ('firstname', 'lastname',)}
        ma = NameModelAdmin(models.NameModel, self.site)
        self.assertEqual(ma.prepopulated_fields, {'slug': ('firstname_en', 'lastname_en',)})


class ThirdPartyAppIntegrationTest(ModeltranslationTestBase):
    """
    This test case and a test case below have identical tests. The models they test have the same
    definition - but in this case the model is not registered for translation and in the other
    case it is.
    """
    registered = False

    @classmethod
    def setUpClass(cls):
        # 'model' attribute cannot be assigned to class in its definition,
        # because ``models`` module will be reloaded and hence class would use old model classes.
        super(ThirdPartyAppIntegrationTest, cls).setUpClass()
        cls.model = models.ThirdPartyModel

    def test_form(self):
        class CreationForm(forms.ModelForm):
            class Meta:
                model = self.model

        creation_form = CreationForm({'name': 'abc'})
        inst = creation_form.save()
        self.assertEqual('de', get_language())
        self.assertEqual('abc', inst.name)
        self.assertEqual(1, self.model.objects.count())


class ThirdPartyAppIntegrationRegisteredTest(ThirdPartyAppIntegrationTest):
    registered = True

    @classmethod
    def setUpClass(cls):
        super(ThirdPartyAppIntegrationRegisteredTest, cls).setUpClass()
        cls.model = models.ThirdPartyRegisteredModel


class TestManager(ModeltranslationTestBase):
    def setUp(self):
        # In this test case the default language is en, not de.
        super(TestManager, self).setUp()
        trans_real.activate('en')

    def test_filter_update(self):
        """Test if filtering and updating is language-aware."""
        n = models.ManagerTestModel(title='')
        n.title_en = 'en'
        n.title_de = 'de'
        n.save()

        m = models.ManagerTestModel(title='')
        m.title_en = 'title en'
        m.title_de = 'de'
        m.save()

        self.assertEqual('en', get_language())

        self.assertEqual(0, models.ManagerTestModel.objects.filter(title='de').count())
        self.assertEqual(1, models.ManagerTestModel.objects.filter(title='en').count())
        # Spanning works
        self.assertEqual(2, models.ManagerTestModel.objects.filter(title__contains='en').count())

        with override('de'):
            self.assertEqual(2, models.ManagerTestModel.objects.filter(title='de').count())
            self.assertEqual(0, models.ManagerTestModel.objects.filter(title='en').count())
            # Spanning works
            self.assertEqual(2, models.ManagerTestModel.objects.filter(title__endswith='e').count())

            # Still possible to use explicit language version
            self.assertEqual(1, models.ManagerTestModel.objects.filter(title_en='en').count())
            self.assertEqual(2, models.ManagerTestModel.objects.filter(
                             title_en__contains='en').count())

            models.ManagerTestModel.objects.update(title='new')
            self.assertEqual(2, models.ManagerTestModel.objects.filter(title='new').count())
            n = models.ManagerTestModel.objects.get(pk=n.pk)
            m = models.ManagerTestModel.objects.get(pk=m.pk)
            self.assertEqual('en', n.title_en)
            self.assertEqual('new', n.title_de)
            self.assertEqual('title en', m.title_en)
            self.assertEqual('new', m.title_de)

    def test_q(self):
        """Test if Q queries are rewritten."""
        n = models.ManagerTestModel(title='')
        n.title_en = 'en'
        n.title_de = 'de'
        n.save()

        self.assertEqual('en', get_language())
        self.assertEqual(0, models.ManagerTestModel.objects.filter(Q(title='de')
                                                                   | Q(pk=42)).count())
        self.assertEqual(1, models.ManagerTestModel.objects.filter(Q(title='en')
                                                                   | Q(pk=42)).count())

        with override('de'):
            self.assertEqual(1, models.ManagerTestModel.objects.filter(Q(title='de')
                                                                       | Q(pk=42)).count())
            self.assertEqual(0, models.ManagerTestModel.objects.filter(Q(title='en')
                                                                       | Q(pk=42)).count())

    def test_f(self):
        """Test if F queries are rewritten."""
        n = models.ManagerTestModel.objects.create(visits_en=1, visits_de=2)

        self.assertEqual('en', get_language())
        models.ManagerTestModel.objects.update(visits=F('visits') + 10)
        n = models.ManagerTestModel.objects.all()[0]
        self.assertEqual(n.visits_en, 11)
        self.assertEqual(n.visits_de, 2)

        with override('de'):
            models.ManagerTestModel.objects.update(visits=F('visits') + 20)
            n = models.ManagerTestModel.objects.all()[0]
            self.assertEqual(n.visits_en, 11)
            self.assertEqual(n.visits_de, 22)

    def test_order_by(self):
        """Check that field names are rewritten in order_by keys."""
        manager = models.ManagerTestModel.objects
        manager.create(title='a')
        m = manager.create(title='b')
        manager.create(title='c')
        with override('de'):
            # Make the order of the 'title' column different.
            m.title = 'd'
            m.save()
        titles_asc = tuple(m.title for m in manager.order_by('title'))
        titles_desc = tuple(m.title for m in manager.order_by('-title'))
        self.assertEqual(titles_asc, ('a', 'b', 'c'))
        self.assertEqual(titles_desc, ('c', 'b', 'a'))

    def test_order_by_meta(self):
        """Check that meta ordering is rewritten."""
        manager = models.ManagerTestModel.objects
        manager.create(title='more_de', visits_en=1, visits_de=2)
        manager.create(title='more_en', visits_en=2, visits_de=1)
        manager.create(title='most', visits_en=3, visits_de=3)
        manager.create(title='least', visits_en=0, visits_de=0)

        # Ordering descending with visits_en
        titles_for_en = tuple(m.title_en for m in manager.all())
        with override('de'):
            # Ordering descending with visits_de
            titles_for_de = tuple(m.title_en for m in manager.all())

        self.assertEqual(titles_for_en, ('most', 'more_en', 'more_de', 'least'))
        self.assertEqual(titles_for_de, ('most', 'more_de', 'more_en', 'least'))

    def test_custom_manager(self):
        """Test if user-defined manager is still working"""
        n = models.CustomManagerTestModel(title='')
        n.title_en = 'enigma'
        n.title_de = 'foo'
        n.save()

        m = models.CustomManagerTestModel(title='')
        m.title_en = 'enigma'
        m.title_de = 'bar'
        m.save()

        # Custom method
        self.assertEqual('bar', models.CustomManagerTestModel.objects.foo())

        # Ensure that get_query_set is working - filter objects to those with 'a' in title
        self.assertEqual('en', get_language())
        self.assertEqual(2, models.CustomManagerTestModel.objects.count())
        with override('de'):
            self.assertEqual(1, models.CustomManagerTestModel.objects.count())

    def test_custom_manager2(self):
        """Test if user-defined queryset is still working"""
        from modeltranslation.manager import MultilingualManager, MultilingualQuerySet
        manager = models.CustomManager2TestModel.objects
        self.assertTrue(isinstance(manager, models.CustomManager2))
        self.assertTrue(isinstance(manager, MultilingualManager))
        qs = manager.all()
        self.assertTrue(isinstance(qs, models.CustomQuerySet))
        self.assertTrue(isinstance(qs, MultilingualQuerySet))

    def test_creation(self):
        """Test if field are rewritten in create."""
        self.assertEqual('en', get_language())
        n = models.ManagerTestModel.objects.create(title='foo')
        self.assertEqual('foo', n.title_en)
        self.assertEqual(None, n.title_de)
        self.assertEqual('foo', n.title)

        # The same result
        n = models.ManagerTestModel.objects.create(title_en='foo')
        self.assertEqual('foo', n.title_en)
        self.assertEqual(None, n.title_de)
        self.assertEqual('foo', n.title)

        # Language suffixed version wins
        n = models.ManagerTestModel.objects.create(title='bar', title_en='foo')
        self.assertEqual('foo', n.title_en)
        self.assertEqual(None, n.title_de)
        self.assertEqual('foo', n.title)

    def test_creation_population(self):
        """Test if language fields are populated with default value on creation."""
        n = models.ManagerTestModel.objects.populate(True).create(title='foo')
        self.assertEqual('foo', n.title_en)
        self.assertEqual('foo', n.title_de)
        self.assertEqual('foo', n.title)

        # You can specify some language...
        n = models.ManagerTestModel.objects.populate(True).create(title='foo', title_de='bar')
        self.assertEqual('foo', n.title_en)
        self.assertEqual('bar', n.title_de)
        self.assertEqual('foo', n.title)

        # ... but remember that still original attribute points to current language
        self.assertEqual('en', get_language())
        n = models.ManagerTestModel.objects.populate(True).create(title='foo', title_en='bar')
        self.assertEqual('bar', n.title_en)
        self.assertEqual('foo', n.title_de)
        self.assertEqual('bar', n.title)  # points to en
        with override('de'):
            self.assertEqual('foo', n.title)  # points to de
        self.assertEqual('en', get_language())

        # This feature (for backward-compatibility) require populate method...
        n = models.ManagerTestModel.objects.create(title='foo')
        self.assertEqual('foo', n.title_en)
        self.assertEqual(None, n.title_de)
        self.assertEqual('foo', n.title)

        # ... or MODELTRANSLATION_AUTO_POPULATE setting
        with reload_override_settings(MODELTRANSLATION_AUTO_POPULATE=True):
            self.assertEqual(True, mt_settings.AUTO_POPULATE)
            n = models.ManagerTestModel.objects.create(title='foo')
            self.assertEqual('foo', n.title_en)
            self.assertEqual('foo', n.title_de)
            self.assertEqual('foo', n.title)

            # populate method has highest priority
            n = models.ManagerTestModel.objects.populate(False).create(title='foo')
            self.assertEqual('foo', n.title_en)
            self.assertEqual(None, n.title_de)
            self.assertEqual('foo', n.title)

        # Populate ``default`` fills just the default translation.
        # TODO: Having more languages would make these tests more meaningful.
        qs = models.ManagerTestModel.objects
        m = qs.populate('default').create(title='foo', description='bar')
        self.assertEqual('foo', m.title_de)
        self.assertEqual('foo', m.title_en)
        self.assertEqual('bar', m.description_de)
        self.assertEqual('bar', m.description_en)
        with override('de'):
            m = qs.populate('default').create(title='foo', description='bar')
            self.assertEqual('foo', m.title_de)
            self.assertEqual(None, m.title_en)
            self.assertEqual('bar', m.description_de)
            self.assertEqual(None, m.description_en)

        # Populate ``required`` fills just non-nullable default translations.
        qs = models.ManagerTestModel.objects
        m = qs.populate('required').create(title='foo', description='bar')
        self.assertEqual('foo', m.title_de)
        self.assertEqual('foo', m.title_en)
        self.assertEqual(None, m.description_de)
        self.assertEqual('bar', m.description_en)
        with override('de'):
            m = qs.populate('required').create(title='foo', description='bar')
            self.assertEqual('foo', m.title_de)
            self.assertEqual(None, m.title_en)
            self.assertEqual('bar', m.description_de)
            self.assertEqual(None, m.description_en)

    def test_get_or_create_population(self):
        """
        Populate may be used with ``get_or_create``.
        """
        qs = models.ManagerTestModel.objects
        m1, created1 = qs.populate(True).get_or_create(title='aaa')
        m2, created2 = qs.populate(True).get_or_create(title='aaa')
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(m1, m2)
        self.assertEqual('aaa', m1.title_en)
        self.assertEqual('aaa', m1.title_de)

    def test_fixture_population(self):
        """
        Test that a fixture with values only for the original fields
        does not result in missing default translations for (original)
        non-nullable fields.
        """
        with auto_populate('required'):
            call_command('loaddata', 'fixture.json', verbosity=0, commit=False)
            m = models.TestModel.objects.get()
            self.assertEqual(m.title_en, 'foo')
            self.assertEqual(m.title_de, 'foo')
            self.assertEqual(m.text_en, 'bar')
            self.assertEqual(m.text_de, None)

    def test_fixture_population_via_command(self):
        """
        Test that the loaddata command takes new option.
        """
        call_command('loaddata', 'fixture.json', verbosity=0, commit=False, populate='required')
        m = models.TestModel.objects.get()
        self.assertEqual(m.title_en, 'foo')
        self.assertEqual(m.title_de, 'foo')
        self.assertEqual(m.text_en, 'bar')
        self.assertEqual(m.text_de, None)

        call_command('loaddata', 'fixture.json', verbosity=0, commit=False, populate='all')
        m = models.TestModel.objects.get()
        self.assertEqual(m.title_en, 'foo')
        self.assertEqual(m.title_de, 'foo')
        self.assertEqual(m.text_en, 'bar')
        self.assertEqual(m.text_de, 'bar')

        # Test if option overrides current context
        with auto_populate('all'):
            call_command('loaddata', 'fixture.json', verbosity=0, commit=False, populate=False)
            m = models.TestModel.objects.get()
            self.assertEqual(m.title_en, 'foo')
            self.assertEqual(m.title_de, None)
            self.assertEqual(m.text_en, 'bar')
            self.assertEqual(m.text_de, None)

    def assertDeferred(self, use_defer, *fields):
        manager = models.TestModel.objects.defer if use_defer else models.TestModel.objects.only
        inst1 = manager(*fields)[0]
        with override('de'):
            inst2 = manager(*fields)[0]
        self.assertEqual('title_en', inst1.title)
        self.assertEqual('title_en', inst2.title)
        with override('de'):
            self.assertEqual('title_de', inst1.title)
            self.assertEqual('title_de', inst2.title)

    def test_deferred(self):
        """
        Check if ``only`` and ``defer`` are working.
        """
        models.TestModel.objects.create(title_de='title_de', title_en='title_en')
        inst = models.TestModel.objects.only('title_en')[0]
        self.assertNotEqual(inst.__class__, models.TestModel)
        self.assertTrue(isinstance(inst, models.TestModel))
        self.assertDeferred(False, 'title_en')

        with auto_populate('all'):
            self.assertDeferred(False, 'title')
            self.assertDeferred(False, 'title_de')
            self.assertDeferred(False, 'title_en')
            self.assertDeferred(False, 'title_en', 'title_de')
            self.assertDeferred(False, 'title', 'title_en')
            self.assertDeferred(False, 'title', 'title_de')
            # Check if fields are deferred properly with ``only``
            self.assertDeferred(False, 'text')

            # Defer
            self.assertDeferred(True, 'title')
            self.assertDeferred(True, 'title_de')
            self.assertDeferred(True, 'title_en')
            self.assertDeferred(True, 'title_en', 'title_de')
            self.assertDeferred(True, 'title', 'title_en')
            self.assertDeferred(True, 'title', 'title_de')
            self.assertDeferred(True, 'text', 'email', 'url')
