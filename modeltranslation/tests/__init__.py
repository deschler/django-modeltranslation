# -*- coding: utf-8 -*-
"""
NOTE: Perhaps ModeltranslationTestBase in tearDownClass should reload some modules,
      so that tests for other apps are in the same environment.

"""
from __future__ import with_statement  # Python 2.5 compatibility
import datetime
from decimal import Decimal
import os
import shutil

from django import forms
from django.conf import settings as django_settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.db.models import Q, F
from django.db.models.loading import AppCache
from django.test import TestCase
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
from modeltranslation.utils import build_css_class, build_localized_fieldname

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

# How much models are registered for tests.
TEST_MODELS = 22


class reload_override_settings(override_settings):
    """Context manager that not only override settings, but also reload modeltranslation conf."""
    def __enter__(self):
        super(reload_override_settings, self).__enter__()
        reload(mt_settings)

    def __exit__(self, exc_type, exc_value, traceback):
        super(reload_override_settings, self).__exit__(exc_type, exc_value, traceback)
        reload(mt_settings)


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
                reload(translation)

                # 2. Reload MT because LANGUAGES likely changed.
                reload(mt_settings)
                reload(translator)
                reload(admin)

                # 3. Reset test models (because autodiscover have already run, those models
                #    have translation fields, but for languages previously defined. We want
                #    to be sure that 'de' and 'en' are available)
                del cls.cache.app_models['tests']
                reload(models)
                cls.cache.load_app('modeltranslation.tests')
                sys.modules.pop('modeltranslation.tests.translation', None)

                # 4. Autodiscover
                from modeltranslation import models as aut_models
                reload(aut_models)

                # 5. Syncdb (``migrate=False`` in case of south)
                from django.db import connections, DEFAULT_DB_ALIAS
                call_command('syncdb', verbosity=0, migrate=False, interactive=False,
                             database=connections[DEFAULT_DB_ALIAS].alias, load_initial_data=False)

    def setUp(self):
        trans_real.activate('de')

    def tearDown(self):
        trans_real.deactivate()

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
        from django.conf import settings
        new_installed_apps = settings.INSTALLED_APPS + ('modeltranslation.tests.test_app',)
        self.__override = override_settings(INSTALLED_APPS=new_installed_apps)
        self.__override.enable()

    def _post_teardown(self):
        self.__override.disable()
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
        from test_app import models
        reload(models)
        # Delete translation modules from import cache
        sys.modules.pop('modeltranslation.tests.test_app.translation', None)
        sys.modules.pop('modeltranslation.tests.project_translation', None)

    def check_news(self):
        from test_app.models import News
        fields = dir(News())
        self.assertIn('title', fields)
        self.assertIn('title_en', fields)
        self.assertIn('title_de', fields)
        self.assertIn('visits', fields)
        self.assertNotIn('visits_en', fields)
        self.assertNotIn('visits_de', fields)

    def check_other(self, present=True):
        from test_app.models import Other
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

    @reload_override_settings(
        MODELTRANSLATION_TRANSLATION_REGISTRY='modeltranslation.tests.project_translation'
    )
    def test_backward_compatibility(self):
        """Check if old modeltranslation configuration (with REGISTRY) is handled properly."""
        autodiscover()
        self.check_news()
        self.check_other()


class ModeltranslationTest(ModeltranslationTestBase):
    """Basic tests for the modeltranslation application."""
    def test_registration(self):
        langs = tuple(l[0] for l in django_settings.LANGUAGES)
        self.failUnlessEqual(langs, tuple(mt_settings.AVAILABLE_LANGUAGES))
        self.failUnlessEqual(2, len(langs))
        self.failUnless('de' in langs)
        self.failUnless('en' in langs)
        self.failUnless(translator.translator)

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
        self.failUnless('id' in field_names)
        self.failUnless('title' in field_names)
        self.failUnless('title_de' in field_names)
        self.failUnless('title_en' in field_names)
        self.failUnless('text' in field_names)
        self.failUnless('text_de' in field_names)
        self.failUnless('text_en' in field_names)
        self.failUnless('url' in field_names)
        self.failUnless('url_de' in field_names)
        self.failUnless('url_en' in field_names)
        self.failUnless('email' in field_names)
        self.failUnless('email_de' in field_names)
        self.failUnless('email_en' in field_names)

    def test_verbose_name(self):
        verbose_name = models.TestModel._meta.get_field('title_de').verbose_name
        self.assertEquals(unicode(verbose_name), u'title [de]')

    def test_descriptor_introspection(self):
        # See Django #8248
        try:
            models.TestModel.title
            models.TestModel.title.__doc__
            self.assertTrue(True)
        except:
            self.fail('Descriptor accessed on class should return itself.')

    def test_set_translation(self):
        """This test briefly shows main modeltranslation features."""
        self.failUnlessEqual(get_language(), 'de')
        title_de = "title de"
        title_en = "title en"

        # The original field "title" passed in the constructor is
        # populated for the current language field: "title_de".
        inst2 = models.TestModel(title=title_de)
        self.failUnlessEqual(inst2.title, title_de)
        self.failUnlessEqual(inst2.title_en, None)
        self.failUnlessEqual(inst2.title_de, title_de)

        # So creating object is language-aware
        with override('en'):
            inst2 = models.TestModel(title=title_en)
            self.failUnlessEqual(inst2.title, title_en)
            self.failUnlessEqual(inst2.title_en, title_en)
            self.failUnlessEqual(inst2.title_de, None)

        # Value from original field is presented in current language:
        inst2 = models.TestModel(title_de=title_de, title_en=title_en)
        self.failUnlessEqual(inst2.title, title_de)
        with override('en'):
            self.failUnlessEqual(inst2.title, title_en)

        # Changes made via original field affect current language field:
        inst2.title = 'foo'
        self.failUnlessEqual(inst2.title, 'foo')
        self.failUnlessEqual(inst2.title_en, title_en)
        self.failUnlessEqual(inst2.title_de, 'foo')
        with override('en'):
            inst2.title = 'bar'
            self.failUnlessEqual(inst2.title, 'bar')
            self.failUnlessEqual(inst2.title_en, 'bar')
            self.failUnlessEqual(inst2.title_de, 'foo')
        self.failUnlessEqual(inst2.title, 'foo')

        # When conflict, language field wins with original field
        inst2 = models.TestModel(title='foo', title_de=title_de, title_en=title_en)
        self.failUnlessEqual(inst2.title, title_de)
        self.failUnlessEqual(inst2.title_en, title_en)
        self.failUnlessEqual(inst2.title_de, title_de)

        # Creating model and assigning only one language
        inst1 = models.TestModel(title_en=title_en)
        # Please note: '' and not None, because descriptor falls back to field default value
        self.failUnlessEqual(inst1.title, '')
        self.failUnlessEqual(inst1.title_en, title_en)
        self.failUnlessEqual(inst1.title_de, None)
        # Assign current language value - de
        inst1.title = title_de
        self.failUnlessEqual(inst1.title, title_de)
        self.failUnlessEqual(inst1.title_en, title_en)
        self.failUnlessEqual(inst1.title_de, title_de)
        inst1.save()

        # Check that the translation fields are correctly saved and provide the
        # correct value when retrieving them again.
        n = models.TestModel.objects.get(title=title_de)
        self.failUnlessEqual(n.title, title_de)
        self.failUnlessEqual(n.title_en, title_en)
        self.failUnlessEqual(n.title_de, title_de)

        # Queries are also language-aware:
        self.failUnlessEqual(1, models.TestModel.objects.filter(title=title_de).count())
        with override('en'):
            self.failUnlessEqual(0, models.TestModel.objects.filter(title=title_de).count())

    def test_fallback_language(self):
        # Present what happens if current language field is empty
        self.failUnlessEqual(get_language(), 'de')
        title_de = "title de"

        # Create model with value in de only...
        inst2 = models.TestModel(title=title_de)
        self.failUnlessEqual(inst2.title, title_de)
        self.failUnlessEqual(inst2.title_en, None)
        self.failUnlessEqual(inst2.title_de, title_de)

        # In this test environment, fallback language is not set. So return value for en
        # will be field's default: ''
        with override('en'):
            self.failUnlessEqual(inst2.title, '')
            self.failUnlessEqual(inst2.title_en, None)  # Language field access returns real value

        # However, by default FALLBACK_LANGUAGES is set to DEFAULT_LANGUAGE
        with default_fallback():

            # No change here...
            self.failUnlessEqual(inst2.title, title_de)

            # ... but for empty en fall back to de
            with override('en'):
                self.failUnlessEqual(inst2.title, title_de)
                self.failUnlessEqual(inst2.title_en, None)  # Still real value

    def test_fallback_values_1(self):
        """
        If ``fallback_values`` is set to string, all untranslated fields would
        return this string.
        """
        title1_de = "title de"
        n = models.FallbackModel(title=title1_de)
        n.save()
        n = models.FallbackModel.objects.get(title=title1_de)
        self.failUnlessEqual(n.title, title1_de)
        trans_real.activate("en")
        self.failUnlessEqual(n.title, "fallback")

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
        self.failUnlessEqual(n.title, '')  # Falling back to default field value
        self.failUnlessEqual(
            n.text,
            FallbackModel2TranslationOptions.fallback_values['text'])

    def _compare_instances(self, x, y, field):
        self.assertEqual(getattr(x, field), getattr(y, field),
                         "Constructor diff on field %s." % field)

    def _test_constructor(self, keywords):
        n = models.TestModel(**keywords)
        m = models.TestModel.objects.create(**keywords)
        opts = translator.translator.get_options_for_model(models.TestModel)
        for base_field, trans_fields in opts.fields.iteritems():
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
            self.assertRaises(ImproperlyConfigured, lambda: reload(mt_settings))
        reload(mt_settings)

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


class FileFieldsTest(ModeltranslationTestBase):
    test_media_root = TEST_SETTINGS['MEDIA_ROOT']

    def tearDown(self):
        # File tests create a temporary media directory structure. While the
        # files are automatically deleted by the storage, the directories will
        # stay. So we clean up a bit...
        if os.path.isdir(self.test_media_root):
            shutil.rmtree(self.test_media_root)
        trans_real.deactivate()

    def test_translated_models(self):
        field_names = dir(models.FileFieldsModel())
        self.failUnless('id' in field_names)
        self.failUnless('title' in field_names)
        self.failUnless('title_de' in field_names)
        self.failUnless('title_en' in field_names)
        self.failUnless('file' in field_names)
        self.failUnless('file_de' in field_names)
        self.failUnless('file_en' in field_names)
        self.failUnless('image' in field_names)
        self.failUnless('image_de' in field_names)
        self.failUnless('image_en' in field_names)

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
        self.failUnlessEqual(inst.title, 'title_en')
        self.failUnless(inst.file.name.count('b_en') > 0)
        self.failUnlessEqual(inst.file.read(), 'file in english')
        self.failUnless(inst.image.name.count('i_en') > 0)
        self.failUnlessEqual(inst.image.read(), 'image in english')

        # Check if file was actually saved on disc
        self.failUnless(os.path.exists(os.path.join(self.test_media_root, inst.file.name)))
        self.failUnless(inst.file.size > 0)
        self.failUnless(os.path.exists(os.path.join(self.test_media_root, inst.image.name)))
        self.failUnless(inst.image.size > 0)

        trans_real.activate("de")
        self.failUnlessEqual(inst.title, 'title_de')
        self.failUnless(inst.file.name.count('b_de') > 0)
        self.failUnlessEqual(inst.file.read(), 'file in german')
        self.failUnless(inst.image.name.count('i_de') > 0)
        self.failUnlessEqual(inst.image.read(), 'image in german')

        inst.file_en.delete()
        inst.image_en.delete()
        inst.file_de.delete()
        inst.image_de.delete()


class OtherFieldsTest(ModeltranslationTestBase):
    def test_translated_models(self):
        inst = models.OtherFieldsModel.objects.create()
        field_names = dir(inst)
        self.failUnless('id' in field_names)
        self.failUnless('int' in field_names)
        self.failUnless('int_de' in field_names)
        self.failUnless('int_en' in field_names)
        self.failUnless('boolean' in field_names)
        self.failUnless('boolean_de' in field_names)
        self.failUnless('boolean_en' in field_names)
        self.failUnless('nullboolean' in field_names)
        self.failUnless('nullboolean_de' in field_names)
        self.failUnless('nullboolean_en' in field_names)
        self.failUnless('csi' in field_names)
        self.failUnless('csi_de' in field_names)
        self.failUnless('csi_en' in field_names)
        self.failUnless('ip' in field_names)
        self.failUnless('ip_de' in field_names)
        self.failUnless('ip_en' in field_names)
#        self.failUnless('genericip' in field_names)
#        self.failUnless('genericip_de' in field_names)
#        self.failUnless('genericip_en' in field_names)
        self.failUnless('float' in field_names)
        self.failUnless('float_de' in field_names)
        self.failUnless('float_en' in field_names)
        self.failUnless('decimal' in field_names)
        self.failUnless('decimal_de' in field_names)
        self.failUnless('decimal_en' in field_names)
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

        inst.time = datetime.time(01, 02, 03)
        inst.save()
        self.assertEqual(datetime.time(01, 02, 03), inst.time)
        self.assertEqual(datetime.time(01, 02, 03), inst.time_de)
        self.assertEqual(None, inst.time_en)

        qs = models.OtherFieldsModel.objects.filter(time='01:02:03')
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0].time, datetime.time(01, 02, 03))

        trans_real.activate('en')
        inst.time = datetime.time(23, 42, 0)
        self.assertEqual(datetime.time(23, 42, 0), inst.time)
        self.assertEqual(datetime.time(01, 02, 03), inst.time_de)
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
        self.failUnlessEqual(get_language(), 'de')
        self.failUnlessEqual(getattr(n, field_name), value_de)
        self.failUnlessEqual(getattr(n, field_name_de), value_de)
        self.failUnlessEqual(getattr(n, field_name_en), value_en)
        # Now switch to "en"
        trans_real.activate("en")
        self.failUnlessEqual(get_language(), "en")
        # Should now be return the english one (just by switching the language)
        self.failUnlessEqual(getattr(n, field_name), value_en)
        # But explicit language fields hold their values
        self.failUnlessEqual(getattr(n, field_name_de), value_de)
        self.failUnlessEqual(getattr(n, field_name_en), value_en)

        n = models.TestModel.objects.create(**params)
        n.save()
        # Language is set to "en" at this point
        self.failUnlessEqual(get_language(), "en")
        self.failUnlessEqual(getattr(n, field_name), value_en)
        self.failUnlessEqual(getattr(n, field_name_de), value_de)
        self.failUnlessEqual(getattr(n, field_name_en), value_en)
        trans_real.activate('de')
        self.failUnlessEqual(get_language(), 'de')
        self.failUnlessEqual(getattr(n, field_name), value_de)

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

        self.failUnlessEqual(get_language(), 'de')
        n = models.TestModel.objects.create(**params)
        self.failUnlessEqual(getattr(n, field_name), value1_de)
        self.failUnlessEqual(getattr(n, field_name_de), value1_de)
        self.failUnlessEqual(getattr(n, field_name_en), value1_en)

        setattr(n, field_name, value2)
        n.save()
        self.failUnlessEqual(getattr(n, field_name), value2)
        self.failUnlessEqual(getattr(n, field_name_de), value2)
        self.failUnlessEqual(getattr(n, field_name_en), value1_en)

        trans_real.activate("en")
        self.failUnlessEqual(get_language(), "en")

        setattr(n, field_name, value3)
        setattr(n, field_name_de, value1_de)
        n.save()
        self.failUnlessEqual(getattr(n, field_name), value3)
        self.failUnlessEqual(getattr(n, field_name_en), value3)
        self.failUnlessEqual(getattr(n, field_name_de), value1_de)

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
        self.failUnlessEqual(get_language(), 'de')
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
        except ValidationError, e:
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
        self.failUnlessEqual(get_language(), 'de')
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
        self.failUnlessEqual(get_language(), 'de')
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
        self.failIf('titled' in field_names_b)
        self.failIf('titled_de' in field_names_b)
        self.failIf('titled_en' in field_names_b)

    def test_multitable_inheritance(self):
        field_names_a = models.MultitableModelA._meta.get_all_field_names()
        self.failUnless('titlea' in field_names_a)
        self.failUnless('titlea_de' in field_names_a)
        self.failUnless('titlea_en' in field_names_a)

        field_names_b = models.MultitableModelB._meta.get_all_field_names()
        self.failUnless('titlea' in field_names_b)
        self.failUnless('titlea_de' in field_names_b)
        self.failUnless('titlea_en' in field_names_b)
        self.failUnless('titleb' in field_names_b)
        self.failUnless('titleb_de' in field_names_b)
        self.failUnless('titleb_en' in field_names_b)

        field_names_c = models.MultitableModelC._meta.get_all_field_names()
        self.failUnless('titlea' in field_names_c)
        self.failUnless('titlea_de' in field_names_c)
        self.failUnless('titlea_en' in field_names_c)
        self.failUnless('titleb' in field_names_c)
        self.failUnless('titleb_de' in field_names_c)
        self.failUnless('titleb_en' in field_names_c)
        self.failUnless('titlec' in field_names_c)
        self.failUnless('titlec_de' in field_names_c)
        self.failUnless('titlec_en' in field_names_c)

        field_names_d = models.MultitableModelD._meta.get_all_field_names()
        self.failUnless('titlea' in field_names_d)
        self.failUnless('titlea_de' in field_names_d)
        self.failUnless('titlea_en' in field_names_d)
        self.failUnless('titleb' in field_names_d)
        self.failUnless('titleb_de' in field_names_d)
        self.failUnless('titleb_en' in field_names_d)
        self.failUnless('titled' in field_names_d)

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
        self.failUnless('titlea' in clsb.fields)
        self.failUnless('titleb' in clsb.fields)
        self.failUnless('titlec' in clsb.fields)
        self.failUnlessEqual(3, len(clsb.fields))
        self.failUnlessEqual(tuple, type(clsb.fields))

    def test_multi_inheritance(self):
        clsb = FieldInheritanceETranslationOptions
        self.failUnless('titlea' in clsb.fields)
        self.failUnless('titleb' in clsb.fields)
        self.failUnless('titlec' in clsb.fields)
        self.failUnless('titled' in clsb.fields)
        self.failUnless('titlee' in clsb.fields)
        self.failUnlessEqual(5, len(clsb.fields))  # there are no repetitions


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
        trans_real.activate('de')
        self.test_obj = models.TestModel.objects.create(
            title='Testtitle', text='Testtext')
        self.site = AdminSite()

    def tearDown(self):
        trans_real.deactivate()
        self.test_obj.delete()

    def test_default_fields(self):
        class TestModelAdmin(admin.TranslationAdmin):
            pass

        ma = TestModelAdmin(models.TestModel, self.site)
        self.assertEqual(
            ma.get_form(request).base_fields.keys(),
            ['title_de', 'title_en', 'text_de', 'text_en', 'url_de', 'url_en',
             'email_de', 'email_en'])

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
        self.assertEqual(ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

    def test_field_arguments_restricted_on_form(self):
        # Using `fields`.
        class TestModelAdmin(admin.TranslationAdmin):
            fields = ['title']

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ['title_de', 'title_en']
        self.assertEqual(ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

        # Using `fieldsets`.
        class TestModelAdmin(admin.TranslationAdmin):
            fieldsets = [(None, {'fields': ['title']})]

        ma = TestModelAdmin(models.TestModel, self.site)
        self.assertEqual(ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

        # Using `exclude`.
        class TestModelAdmin(admin.TranslationAdmin):
            exclude = ['url', 'email']

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ['title_de', 'title_en', 'text_de', 'text_en']
        self.assertEqual(
            ma.get_form(request).base_fields.keys(), fields)

        # You can also pass a tuple to `exclude`.
        class TestModelAdmin(admin.TranslationAdmin):
            exclude = ('url', 'email')

        ma = TestModelAdmin(models.TestModel, self.site)
        self.assertEqual(
            ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

        # Using `fields` and `exclude`.
        class TestModelAdmin(admin.TranslationAdmin):
            fields = ['title', 'url']
            exclude = ['url']

        ma = TestModelAdmin(models.TestModel, self.site)
        self.assertEqual(
            ma.get_form(request).base_fields.keys(), ['title_de', 'title_en'])

        # Using `fields` and `readonly_fields`.
        class TestModelAdmin(admin.TranslationAdmin):
            fields = ['title', 'url']
            readonly_fields = ['url']

        ma = TestModelAdmin(models.TestModel, self.site)
        self.assertEqual(
            ma.get_form(request).base_fields.keys(), ['title_de', 'title_en'])

        # Using `readonly_fields`.
        # Note: readonly fields are not included in the form.
        class TestModelAdmin(admin.TranslationAdmin):
            readonly_fields = ['title']

        ma = TestModelAdmin(models.TestModel, self.site)
        self.assertEqual(
            ma.get_form(request).base_fields.keys(),
            ['text_de', 'text_en', 'url_de', 'url_en', 'email_de', 'email_en'])

        # Using grouped fields.
        # Note: Current implementation flattens the nested fields.
        class TestModelAdmin(admin.TranslationAdmin):
            fields = (('title', 'url'), 'email',)

        ma = TestModelAdmin(models.TestModel, self.site)
        self.assertEqual(
            ma.get_form(request).base_fields.keys(),
            ['title_de', 'title_en', 'url_de', 'url_en', 'email_de', 'email_en'])

        # Using grouped fields in `fieldsets`.
        class TestModelAdmin(admin.TranslationAdmin):
            fieldsets = [(None, {'fields': ('email', ('title', 'url'))})]

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ['email_de', 'email_en', 'title_de', 'title_en', 'url_de', 'url_en']
        self.assertEqual(ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

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
            ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

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
            ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

        # If both, the custom form an the ModelAdmin define an `exclude`
        # option, the ModelAdmin wins. This is Django behaviour.
        class TestModelAdmin(admin.TranslationAdmin):
            form = TestModelForm
            exclude = ['url']

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ['title_de', 'title_en', 'text_de', 'text_en', 'email_de',
                  'email_en']
        self.assertEqual(
            ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

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
            ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

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
        fields = {
            'foo_en': 'foo-en', 'foo_es_ar': 'foo-es_ar',
            'foo_bar_de': 'foo_bar-de',
            '_foo_en': '_foo-en', '_foo_es_ar': '_foo-es_ar',
            '_foo_bar_de': '_foo_bar-de',
            'foo__en': 'foo_-en', 'foo__es_ar': 'foo_-es_ar',
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

        self.assertEqual(maa.get_form(request).base_fields.keys(),
                         ['titlea_de', 'titlea_en'])
        self.assertEqual(mab.get_form(request).base_fields.keys(),
                         ['titlea_de', 'titlea_en', 'titleb_de', 'titleb_en'])

    def test_group_fieldsets(self):
        # Declared fieldsets take precedence over group_fieldsets
        class GroupFieldsetsModelAdmin(admin.TranslationAdmin):
            fieldsets = [(None, {'fields': ['title']})]
            group_fieldsets = True
        ma = GroupFieldsetsModelAdmin(models.GroupFieldsetsModel, self.site)
        fields = ['title_de', 'title_en']
        self.assertEqual(ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(ma.get_form(request, self.test_obj).base_fields.keys(), fields)

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
        self.failUnlessEqual(get_language(), 'de')

        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {'slug': ('firstname',)}
        ma = NameModelAdmin(models.NameModel, self.site)
        self.assertEqual(ma.prepopulated_fields, {'slug': ('firstname_de',)})

        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {'slug': ('firstname', 'lastname',)}
        ma = NameModelAdmin(models.NameModel, self.site)
        self.assertEqual(ma.prepopulated_fields, {'slug': ('firstname_de', 'lastname_de',)})

        trans_real.activate('en')
        self.failUnlessEqual(get_language(), 'en')

        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {'slug': ('firstname',)}
        ma = NameModelAdmin(models.NameModel, self.site)
        self.assertEqual(ma.prepopulated_fields, {'slug': ('firstname_en',)})

        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {'slug': ('firstname', 'lastname',)}
        ma = NameModelAdmin(models.NameModel, self.site)
        self.assertEqual(ma.prepopulated_fields, {'slug': ('firstname_en', 'lastname_en',)})


class TestManager(ModeltranslationTestBase):
    def setUp(self):
        # In this test case the default language is en, not de.
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
        n = models.ManagerTestModel.objects.create(title='foo', _populate=True)
        self.assertEqual('foo', n.title_en)
        self.assertEqual('foo', n.title_de)
        self.assertEqual('foo', n.title)

        # You can specify some language...
        n = models.ManagerTestModel.objects.create(title='foo', title_de='bar', _populate=True)
        self.assertEqual('foo', n.title_en)
        self.assertEqual('bar', n.title_de)
        self.assertEqual('foo', n.title)

        # ... but remember that still original attribute points to current language
        self.assertEqual('en', get_language())
        n = models.ManagerTestModel.objects.create(title='foo', title_en='bar', _populate=True)
        self.assertEqual('bar', n.title_en)
        self.assertEqual('foo', n.title_de)
        self.assertEqual('bar', n.title)  # points to en
        with override('de'):
            self.assertEqual('foo', n.title)  # points to de
        self.assertEqual('en', get_language())

        # This feature (for backward-compatibility) require _populate keyword...
        n = models.ManagerTestModel.objects.create(title='foo')
        self.assertEqual('foo', n.title_en)
        self.assertEqual(None, n.title_de)
        self.assertEqual('foo', n.title)

        # ... or MODELTRANSLATION_AUTO_POPULATE setting
        with override_settings(MODELTRANSLATION_AUTO_POPULATE=True):
            reload(mt_settings)
            self.assertEqual(True, mt_settings.AUTO_POPULATE)
            n = models.ManagerTestModel.objects.create(title='foo')
            self.assertEqual('foo', n.title_en)
            self.assertEqual('foo', n.title_de)
            self.assertEqual('foo', n.title)

            # _populate keyword has highest priority
            n = models.ManagerTestModel.objects.create(title='foo', _populate=False)
            self.assertEqual('foo', n.title_en)
            self.assertEqual(None, n.title_de)
            self.assertEqual('foo', n.title)

        # Restore previous state
        reload(mt_settings)
        self.assertEqual(False, mt_settings.AUTO_POPULATE)
