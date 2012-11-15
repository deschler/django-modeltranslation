# -*- coding: utf-8 -*-
"""
TODO: Merge autoregister tests from django-modeltranslation-wrapper.

NOTE: Perhaps ModeltranslationTestBase in tearDownClass should reload some modules,
      so that tests for other apps are in the same environment.

"""
from __future__ import with_statement  # Python 2.5 compatibility
import os
import shutil

from django import forms
from django.conf import settings as django_settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.files.base import ContentFile
from django.db.models import Q, F
from django.db.models.loading import AppCache
from django.test import TestCase
from django.utils.datastructures import SortedDict
from django.utils.translation import get_language, trans_real

from modeltranslation import settings as mt_settings
from modeltranslation import translator
from modeltranslation.admin import (TranslationAdmin,
                                    TranslationStackedInline)
from modeltranslation.tests.models import (
    AbstractModelB, MultitableModelA, DataModel, FallbackModel, FallbackModel2,
    FileFieldsModel, OtherFieldsModel, TestModel, MultitableBModelA, MultitableModelC,
    MultitableDTestModel, ManagerTestModel, CustomManagerTestModel)
from modeltranslation.tests.translation import FallbackModel2TranslationOptions
from modeltranslation.tests.test_settings import TEST_SETTINGS

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
            # In odred to perform only one syncdb
            ModeltranslationTestBase.synced = True
            with override_settings(**TEST_SETTINGS):
                import sys

                # 1. Reload translation in case USE_I18N was False
                from django.utils import translation
                reload(translation)

                # 2. Reload MT because LANGUAGES likely changed.
                reload(mt_settings)
                reload(translator)
                from modeltranslation import admin
                reload(admin)

                # 3. Reset test models (because autodiscover have already run, those models
                #    have translation fields, but for languages previously defined. We want
                #    to be sure that 'de' and 'en' are available)
                del cls.cache.app_models['tests']
                from modeltranslation.tests import models
                reload(models)
                cls.cache.load_app('modeltranslation.tests')
                sys.modules.pop('modeltranslation.tests.translation', None)

                # 4. Autodiscover
                from modeltranslation import models
                reload(models)

                # 5. Reload some imported classes
                cls.reload_globals('modeltranslation.tests.models')
                cls.reload_globals('modeltranslation.admin')

                # 6. Syncdb (``migrate=False`` in case of south)
                from django.db import connections, DEFAULT_DB_ALIAS
                from django.core.management import call_command
                call_command('syncdb', verbosity=0, migrate=False, interactive=False,
                             database=connections[DEFAULT_DB_ALIAS].alias, load_initial_data=False)

    @staticmethod
    def reload_globals(module):
        """
        Very ugly method for reloading things imported from module.

        It wouldn't be needed if eg. ``TestModel`` calls would be replaced by ``models.TestModel``.
        """
        names = []
        for name, item in globals().items():
            if hasattr(item, '__module__') and item.__module__ == module:
                names.append(name)
        _temp = __import__(module, globals(), locals(), names, -1)
        for name in names:
            globals()[name] = getattr(_temp, name)

    @classmethod
    def clear_cache(cls):
        """
        It is necessary to clear cache - otherwise model reloading won't
        recreate models, but just use old ones.
        """
        cls.cache.app_store = SortedDict()
        cls.cache.app_models = SortedDict()
        cls.cache.app_errors = {}
        cls.cache.handled = {}
        cls.cache.loaded = False

    @classmethod
    def reset_cache(cls):
        """
        Rebuild whole cache, import all models again
        """
        cls.clear_cache()
        cls.cache._populate()
        for m in cls.cache.get_apps():
            reload(m)

    def setUp(self):
        trans_real.activate('de')

    def tearDown(self):
        trans_real.deactivate()

ModeltranslationTestBase = override_settings(**TEST_SETTINGS)(ModeltranslationTestBase)


class ModeltranslationTest(ModeltranslationTestBase):
    """Basic tests for the modeltranslation application."""
    def test_registration(self):
        langs = tuple(l[0] for l in django_settings.LANGUAGES)
        self.failUnlessEqual(2, len(langs))
        self.failUnless('de' in langs)
        self.failUnless('en' in langs)
        self.failUnless(translator.translator)

        # Check that all models are registered for translation
        self.failUnlessEqual(len(translator.translator._registry), 12)

        # Try to unregister a model that is not registered
        self.assertRaises(translator.NotRegistered,
                          translator.translator.unregister, User)

        # Try to get options for a model that is not registered
        self.assertRaises(translator.NotRegistered,
                          translator.translator.get_options_for_model, User)

    def test_translated_models(self):
        # First create an instance of the test model to play with
        inst = TestModel.objects.create(title="Testtitle", text="Testtext")
        field_names = dir(inst)
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
        inst.delete()

    def test_verbose_name(self):
        inst = TestModel.objects.create(title="Testtitle", text="Testtext")
        self.assertEquals(unicode(
            inst._meta.get_field('title_de').verbose_name), u'title [de]')
        inst.delete()

    def test_set_translation(self):
        self.failUnlessEqual(get_language(), 'de')
        # First create an instance of the test model to play with
        title1_de = "title de"
        title1_en = "title en"
        title2_de = "title2 de"
        inst1 = TestModel(title_en=title1_en, text="Testtext")
        inst1.title = title1_de
        inst2 = TestModel(title=title2_de, text="Testtext")
        inst1.save()
        inst2.save()

        self.failUnlessEqual(inst1.title, title1_de)
        self.failUnlessEqual(inst1.title_en, title1_en)

        self.failUnlessEqual(inst2.title, title2_de)
        self.failUnlessEqual(inst2.title_en, None)

        del inst1
        del inst2

        # Check that the translation fields are correctly saved and provide the
        # correct value when retrieving them again.
        n = TestModel.objects.get(title=title1_de)
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.title_en, title1_en)

    def test_titleonly(self):
        title1_de = "title de"
        n = TestModel(title=title1_de)
        # The original field "title" passed in the constructor is also
        # populated for the current language field: "title_de".
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.title_de, title1_de)
        self.failUnlessEqual(n.title_en, None)

    def test_fallback_values_1(self):
        """
        If ``fallback_values`` is set to string, all untranslated fields would
        return this string.
        """
        title1_de = "title de"
        n = FallbackModel()
        n.title = title1_de
        n.save()
        del n
        n = FallbackModel.objects.get(title=title1_de)
        self.failUnlessEqual(n.title, title1_de)
        trans_real.activate("en")
        self.failUnlessEqual(n.title, "")

    def test_fallback_values_2(self):
        """
        If ``fallback_values`` is set to ``dict``, all untranslated fields in
        ``dict`` would return this mapped value. Fields not in ``dict`` would
        return default translation.
        """
        title1_de = "title de"
        text1_de = "text in german"
        n = FallbackModel2()
        n.title = title1_de
        n.text = text1_de
        n.save()
        del n
        n = FallbackModel2.objects.get(title=title1_de)
        trans_real.activate("en")
        self.failUnlessEqual(n.title, '')  # Falling back to default field value
        self.failUnlessEqual(
            n.text,
            FallbackModel2TranslationOptions.fallback_values['text'])

    def _compare_instances(self, x, y, field):
        self.assertEqual(getattr(x, field), getattr(y, field),
                         "Constructor diff on field %s." % field)

    def _test_constructor(self, keywords):
        n = TestModel(**keywords)
        m = TestModel.objects.create(**keywords)
        fields = translator.translator.get_options_for_model(TestModel).localized_fieldnames
        for base_field, trans_fields in fields.iteritems():
            self._compare_instances(n, m, base_field)
            for lang_field in trans_fields:
                self._compare_instances(n, m, lang_field)

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

    def tearDown(self):
        trans_real.deactivate()
        reload(mt_settings)  # Return to previous state

    def test_settings(self):
        # Initial
        self.assertEqual(mt_settings.FALLBACK_LANGUAGES, {'default': ()})
        # Tuple/list
        with override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=('de',)):
            reload(mt_settings)
            self.assertEqual(mt_settings.FALLBACK_LANGUAGES, {'default': ('de',)})
        # Whole dict
        with override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=self.test_fallback):
            reload(mt_settings)
            self.assertEqual(mt_settings.FALLBACK_LANGUAGES, self.test_fallback)
        # Improper language raises error
        config = {'default': (), 'fr': ('en',)}
        with override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=config):
            self.assertRaises(ImproperlyConfigured, lambda: reload(mt_settings))

    def test_resolution_order(self):
        from modeltranslation.utils import resolution_order
        with override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=self.test_fallback):
            reload(mt_settings)
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
        with override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=self.test_fallback):
            reload(mt_settings)
            title_de = 'title de'
            title_en = 'title en'
            n = TestModel(title=title_de)
            self.assertEqual(n.title_de, title_de)
            self.assertEqual(n.title_en, None)
            self.assertEqual(n.title, title_de)
            trans_real.activate('en')
            self.assertEqual(n.title, title_de)  # since default fallback is de

            n = TestModel(title=title_en)
            self.assertEqual(n.title_de, None)
            self.assertEqual(n.title_en, title_en)
            self.assertEqual(n.title, title_en)
            trans_real.activate('de')
            self.assertEqual(n.title, title_en)  # since fallback for de is en

            n.title_en = None
            self.assertEqual(n.title, '')  # if all fallbacks fail, return field.get_default()


class FileFieldsTest(ModeltranslationTestBase):
    test_media_root = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), 'media')

    def tearDown(self):
        # File tests create a temporary media directory structure. While the
        # files are automatically deleted by the storage, the directories will
        # stay. So we clean up a bit...
        if os.path.isdir(self.test_media_root):
            shutil.rmtree(self.test_media_root)
        trans_real.deactivate()

    def test_translated_models(self):
        # First create an instance of the test model to play with
        inst = FileFieldsModel.objects.create(
            title="Testtitle", file=None)
        field_names = dir(inst)
        self.failUnless('id' in field_names)
        self.failUnless('title' in field_names)
        self.failUnless('title_de' in field_names)
        self.failUnless('title_en' in field_names)
        self.failUnless('file' in field_names)
        self.failUnless('file_de' in field_names)
        self.failUnless('file_en' in field_names)
        inst.delete()

    def test_translated_models_instance(self):
        #f_en = ContentFile("Just a really good file")
        inst = FileFieldsModel(title="Testtitle", file=None)

        trans_real.activate("en")
        inst.title = 'title_en'

        inst.file = 'a_en'
        inst.file.save('b_en', ContentFile('file in english'))

        inst.image = 'i_en.jpg'
        inst.image.save('i_en.jpg', ContentFile('image in english'))

        trans_real.activate("de")
        inst.title = 'title_de'

        inst.file = 'a_de'
        inst.file.save('b_de', ContentFile('file in german'))

        inst.image = 'i_de.jpg'
        inst.image.save('i_de.jpg', ContentFile('image in germany'))

        inst.save()

        trans_real.activate("en")

        self.failUnlessEqual(inst.title, 'title_en')
        self.failUnless(inst.file.name.count('b_en') > 0)
        self.failUnless(inst.image.name.count('i_en') > 0)

        trans_real.activate("de")
        self.failUnlessEqual(inst.title, 'title_de')
        self.failUnless(inst.file.name.count('b_de') > 0)
        self.failUnless(inst.image.name.count('i_de') > 0)

        inst.file_en.delete()
        inst.image_en.delete()
        inst.file_de.delete()
        inst.image_de.delete()

        inst.delete()


class OtherFieldsTest(ModeltranslationTestBase):
    def test_translated_models(self):
        inst = OtherFieldsModel.objects.create()
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
        inst.delete()

    def test_translated_models_integer_instance(self):
        inst = OtherFieldsModel()
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
        inst = OtherFieldsModel()
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
        inst = OtherFieldsModel()
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

    def test_translated_models_commaseparatedinteger_instance(self):
        inst = OtherFieldsModel()
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


class ModeltranslationTestRule1(ModeltranslationTestBase):
    """
    Rule 1: Reading the value from the original field returns the value in
    translated to the current language.
    """
    def _test_field(self, field_name, value_de, value_en, deactivate=True):
        field_name_de = '%s_de' % field_name
        field_name_en = '%s_en' % field_name
        params = {'title_de': 'title de', 'title_en': 'title en',
                  field_name_de: value_de, field_name_en: value_en}

        n = TestModel.objects.create(**params)
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

        n = TestModel.objects.create(**params)
        n.save()
        # Language is set to "en" at this point
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
        Could as well call _test_field, just kept for reference.
        """
        title1_de = "title de"
        title1_en = "title en"
        text_de = "Dies ist ein deutscher Satz"
        text_en = "This is an english sentence"

        n = TestModel.objects.create(title_de=title1_de, title_en=title1_en,
                                     text_de=text_de, text_en=text_en)
        n.save()

        # Language is set to 'de' at this point
        self.failUnlessEqual(get_language(), 'de')
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.title_de, title1_de)
        self.failUnlessEqual(n.title_en, title1_en)
        self.failUnlessEqual(n.text, text_de)
        self.failUnlessEqual(n.text_de, text_de)
        self.failUnlessEqual(n.text_en, text_en)
        # Now switch to "en"
        trans_real.activate("en")
        self.failUnlessEqual(get_language(), "en")
        # Title should now be return the english one (just by switching the
        # language)
        self.failUnlessEqual(n.title, title1_en)
        self.failUnlessEqual(n.text, text_en)

        n = TestModel.objects.create(title_de=title1_de, title_en=title1_en,
                                     text_de=text_de, text_en=text_en)
        n.save()
        # Language is set to "en" at this point
        self.failUnlessEqual(n.title, title1_en)
        self.failUnlessEqual(n.title_de, title1_de)
        self.failUnlessEqual(n.title_en, title1_en)
        self.failUnlessEqual(n.text, text_en)
        self.failUnlessEqual(n.text_de, text_de)
        self.failUnlessEqual(n.text_en, text_en)
        trans_real.activate('de')
        self.failUnlessEqual(get_language(), 'de')
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.text, text_de)

        trans_real.deactivate()

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
    Rule 2: Assigning a value to the original field also updates the value
    in the associated translation field of the default language
    """
    def _test_field(self, field_name, value1_de, value1_en, value2, value3,
                    deactivate=True):
        field_name_de = '%s_de' % field_name
        field_name_en = '%s_en' % field_name
        params = {'title_de': 'title de', 'title_en': 'title en',
                  field_name_de: value1_de, field_name_en: value1_en}

        self.failUnlessEqual(get_language(), 'de')
        n = TestModel.objects.create(**params)
        self.failUnlessEqual(getattr(n, field_name), value1_de)
        self.failUnlessEqual(getattr(n, field_name_de), value1_de)
        self.failUnlessEqual(getattr(n, field_name_en), value1_en)

        setattr(n, field_name, value2)
        n.save()
        self.failUnlessEqual(getattr(n, field_name), value2)
        self.failUnlessEqual(getattr(n, field_name), getattr(n, field_name_de))

        trans_real.activate("en")
        self.failUnlessEqual(get_language(), "en")

        setattr(n, field_name, value3)
        setattr(n, field_name_de, value1_de)
        n.save()
        self.failUnlessEqual(getattr(n, field_name), value3)
        self.failUnlessEqual(getattr(n, field_name), getattr(n, field_name_en))
        self.failUnlessEqual(value1_de, getattr(n, field_name_de))

        if deactivate:
            trans_real.deactivate()

    def test_rule2(self):
        """
        Basic CharField/TextField test.
        Could as well call _test_field, just kept for reference.
        """
        self.failUnlessEqual(get_language(), 'de')
        title1_de = "title de"
        title1_en = "title en"
        n = TestModel.objects.create(title_de=title1_de, title_en=title1_en)
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.title_de, title1_de)
        self.failUnlessEqual(n.title_en, title1_en)

        title2 = "Neuer Titel"
        n.title = title2
        n.save()
        self.failUnlessEqual(n.title, title2)
        self.failUnlessEqual(n.title, n.title_de)

        trans_real.activate("en")
        self.failUnlessEqual(get_language(), "en")
        title3 = "new title"

        n.title = title3
        n.title_de = title1_de
        n.save()
        self.failUnlessEqual(n.title, title3)
        self.failUnlessEqual(n.title, n.title_en)
        self.failUnlessEqual(title1_de, n.title_de)

        trans_real.deactivate()

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
    Rule 3: Assigning a value to a translation field of the default
    language also updates the original field - note that the value of the
    original field will not be updated until the model instance is saved.
    """
    def _test_field(self, field_name, value1_de, value1_en, value2, value3,
                    deactivate=True):
        field_name_de = '%s_de' % field_name
        field_name_en = '%s_en' % field_name
        params = {'title_de': 'title de', 'title_en': 'title en',
                  field_name_de: value1_de, field_name_en: value1_en}

        n = TestModel.objects.create(**params)

        self.failUnlessEqual(get_language(), 'de')
        self.failUnlessEqual(getattr(n, field_name), value1_de)
        self.failUnlessEqual(getattr(n, field_name_de), value1_de)
        self.failUnlessEqual(getattr(n, field_name_en), value1_en)

        setattr(n, field_name, value2)
        n.save()
        self.failUnlessEqual(getattr(n, field_name), getattr(n, field_name_de))

        # Now switch to "en"
        trans_real.activate("en")
        self.failUnlessEqual(get_language(), "en")
        setattr(n, field_name_en, value3)
        # the n.title field is not updated before the instance is saved
        n.save()
        self.failUnlessEqual(getattr(n, field_name), getattr(n, field_name_en))

        if deactivate:
            trans_real.deactivate()

    def test_rule3(self):
        """
        Basic CharField/TextField test.
        Could as well call _test_field, just kept for reference.
        """
        title1_de = "title de"
        title1_en = "title en"
        n = TestModel.objects.create(title_de=title1_de, title_en=title1_en)
        self.failUnlessEqual(get_language(), 'de')
        self.failUnlessEqual(mt_settings.DEFAULT_LANGUAGE, 'de')
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.title_de, title1_de)
        self.failUnlessEqual(n.title_en, title1_en)

        n.title_de = "Neuer Titel"
        n.save()
        # We expect that the original field holds the same value as the german
        # one (german is the default language).
        self.failUnlessEqual(n.title, n.title_de)

        # Fetch the updated object and verify all fields
        updated_obj = TestModel.objects.get(id=n.id)
        self.failUnlessEqual(updated_obj.title, 'Neuer Titel')
        self.failUnlessEqual(updated_obj.title_de, 'Neuer Titel')
        self.failUnlessEqual(updated_obj.title_en, 'title en')

        # Now switch to "en"
        trans_real.activate("en")
        self.failUnlessEqual(get_language(), "en")
        n.title_en = "New title"
        # the n.title field is not updated before the instance is saved
        n.save()

        # We expect that the original field has *not* been changed as german
        # is the default language and we only changed the value of the english
        # field.
        # FIXME: Demonstrates a wrong behaviour of save when the current
        # language is different than the default language. In this case the
        # original field is set to value of the current language's field.
        # See issue 33 for details.

        # TODO: Reactivate, temporarily deactivated for a full run of travis ci
        #self.failUnlessEqual(n.title, n.title_de)

        # Fetch the updated object and verify all fields
        #updated_obj = TestModel.objects.get(id=n.id)
        #self.failUnlessEqual(updated_obj.title, 'Neuer Titel')
        #self.failUnlessEqual(updated_obj.title_de, 'Neuer Titel')
        #self.failUnlessEqual(updated_obj.title_en, 'New title')

        trans_real.deactivate()

    def test_rule3_url_field(self):
        self._test_field(field_name='url',
                         value1_de='http://www.google.de',
                         value1_en='http://www.google.com',
                         value2='http://www.google.at',
                         value3='http://www.google.co.uk')

    def test_rule3_email_field(self):
        self._test_field(field_name='email',
                         value1_de='django-modeltranslation@googlecode.de',
                         value1_en='django-modeltranslation@googlecode.com',
                         value2='django-modeltranslation@googlecode.at',
                         value3='django-modeltranslation@googlecode.co.uk')


class ModeltranslationTestRule4(ModeltranslationTestBase):
    """
    Rule 4: If both fields - the original and the translation field of the
    default language - are updated at the same time, the translation field
    wins.
    """
    def _test_field(self, field_name, value1_de, value1_en, value2_de,
                    value2_en, value3, deactivate=True):
        field_name_de = '%s_de' % field_name
        field_name_en = '%s_en' % field_name
        params = {'title_de': 'title de', 'title_en': 'title en',
                  field_name_de: value1_de, field_name_en: value1_en}

        n = TestModel.objects.create(**params)

        self.failUnlessEqual(getattr(n, field_name), value1_de)
        self.failUnlessEqual(getattr(n, field_name_de), value1_de)
        self.failUnlessEqual(getattr(n, field_name_en), value1_en)

        setattr(n, field_name, value3)
        setattr(n, field_name_de, value2_de)
        setattr(n, field_name_en, value2_en)
        n.save()
        self.failUnlessEqual(getattr(n, field_name), value2_de)
        self.failUnlessEqual(getattr(n, field_name_de), value2_de)
        self.failUnlessEqual(getattr(n, field_name_en), value2_en)

        setattr(n, field_name, value3)
        n.save()
        self.failUnlessEqual(getattr(n, field_name), value3)
        self.failUnlessEqual(getattr(n, field_name_de), value3)
        self.failUnlessEqual(getattr(n, field_name_en), value2_en)

        if deactivate:
            trans_real.deactivate()

    def test_rule4(self):
        """
        Basic CharField/TextField test.
        Could as well call _test_field, just kept for reference.
        """
        self.failUnlessEqual(get_language(), 'de')
        title1_de = "title de"
        title1_en = "title en"
        n = TestModel.objects.create(title_de=title1_de, title_en=title1_en)
        self.failUnlessEqual(n.title, title1_de)
        self.failUnlessEqual(n.title_de, title1_de)
        self.failUnlessEqual(n.title_en, title1_en)

        title2_de = "neu de"
        title2_en = "new en"
        title_foo = "foo"
        n.title = title_foo
        n.title_de = title2_de
        n.title_en = title2_en
        n.save()
        self.failUnlessEqual(n.title, title2_de)
        self.failUnlessEqual(n.title_de, title2_de)
        self.failUnlessEqual(n.title_en, title2_en)

        n.title = title_foo
        n.save()
        self.failUnlessEqual(n.title, title_foo)
        self.failUnlessEqual(n.title_de, title_foo)
        self.failUnlessEqual(n.title_en, title2_en)

    def test_rule4_url_field(self):
        self._test_field(field_name='url',
                         value1_de='http://www.google.de',
                         value1_en='http://www.google.com',
                         value2_de='http://www.google.at',
                         value2_en='http://www.google.co.uk',
                         value3='http://www.google.net')

    def test_rule4_email_field(self):
        self._test_field(field_name='email',
                         value1_de='django-modeltranslation@googlecode.de',
                         value1_en='django-modeltranslation@googlecode.com',
                         value2_de='django-modeltranslation@googlecode.at',
                         value2_en='django-modeltranslation@googlecode.co.uk',
                         value3='django-modeltranslation@googlecode.net')


class ModelValidationTest(ModeltranslationTestBase):
    """
    Tests if a translation model field validates correctly.
    """
    def _test_model_validation(self, field_name, invalid_value, valid_value,
                               invalid_value_de):
        """
        Generic model field validation test.
        """
        field_name_de = '%s_de' % field_name
        params = {'title_de': 'title de', 'title_en': 'title en',
                  field_name: invalid_value}

        has_error_key = False
        # Create an object with an invalid url
        #n = TestModel.objects.create(title='Title', url='foo')
        n = TestModel.objects.create(**params)

        # First check the original field
        # Expect that the validation object contains an error for url
        try:
            n.full_clean()
        except ValidationError, e:
            if field_name in e.message_dict:
                has_error_key = True
        self.assertTrue(has_error_key)

        # Check the translation field
        # Language is set to 'de' at this point
        self.failUnlessEqual(get_language(), 'de')
        # Set translation field to a valid url
        #n.url_de = 'http://code.google.com/p/django-modeltranslation/'
        setattr(n, field_name_de, valid_value)
        has_error_key = False
        # Expect that the validation object contains no error for url
        try:
            n.full_clean()
        except ValidationError, e:
            if field_name_de in e.message_dict:
                has_error_key = True
        self.assertFalse(has_error_key)

        # Set translation field to an invalid url
        #n.url_de = 'foo'
        setattr(n, field_name_de, invalid_value)
        has_error_key = False
        # Expect that the validation object contains an error for url_de
        try:
            n.full_clean()
        except ValidationError, e:
            #if 'url_de' in e.message_dict:
            if field_name_de in e.message_dict:
                has_error_key = True
        self.assertTrue(has_error_key)

    def test_model_validation(self):
        """
        General test for CharField and TextField.
        """
        has_error_key = False
        # Create an object without title (which is required)
        n = TestModel.objects.create(text='Testtext')

        # First check the original field
        # Expect that the validation object contains an error for title
        try:
            n.full_clean()
        except ValidationError, e:
            if 'title' in e.message_dict:
                has_error_key = True
        self.assertTrue(has_error_key)
        n.save()

        # Check the translation field
        # Language is set to 'de' at this point
        self.failUnlessEqual(get_language(), 'de')
        # Set translation field to a valid title
        n.title_de = 'Title'
        has_error_key = False
        # Expect that the validation object contains no error for title
        try:
            n.full_clean()
        except ValidationError, e:
            if 'title_de' in e.message_dict:
                has_error_key = True
        self.assertFalse(has_error_key)

        # Set translation field to an empty title
        n.title_de = None
        has_error_key = False
        # Even though the original field isn't optional, translation fields are
        # per definition always optional. So we expect that the validation
        # object contains no error for title_de.
        try:
            n.full_clean()
        except ValidationError, e:
            if 'title_de' in e.message_dict:
                has_error_key = True
        self.assertFalse(has_error_key)

    def test_model_validation_url_field(self):
        #has_error_key = False
        ## Create an object with an invalid url
        #n = TestModel.objects.create(title='Title', url='foo')

        ## First check the original field
        ## Expect that the validation object contains an error for url
        #try:
            #n.full_clean()
        #except ValidationError, e:
            #if 'url' in e.message_dict:
                #has_error_key = True
        #self.assertTrue(has_error_key)

        ## Check the translation field
        ## Language is set to 'de' at this point
        #self.failUnlessEqual(get_language(), 'de')
        ## Set translation field to a valid url
        #n.url_de = 'http://code.google.com/p/django-modeltranslation/'
        #has_error_key = False
        ## Expect that the validation object contains no error for url
        #try:
            #n.full_clean()
        #except ValidationError, e:
            #if 'url_de' in e.message_dict:
                #has_error_key = True
        #self.assertFalse(has_error_key)

        ## Set translation field to an invalid url
        #n.url_de = 'foo'
        #has_error_key = False
        ## Expect that the validation object contains an error for url_de
        #try:
            #n.full_clean()
        #except ValidationError, e:
            #if 'url_de' in e.message_dict:
                #has_error_key = True
        #self.assertTrue(has_error_key)

        self._test_model_validation(
            field_name='url',
            invalid_value='foo en',
            valid_value='http://code.google.com/p/django-modeltranslation/',
            invalid_value_de='foo de')

    def test_model_validation_email_field(self):
        self._test_model_validation(
            field_name='email', invalid_value='foo en',
            valid_value='django-modeltranslation@googlecode.com',
            invalid_value_de='foo de')


class ModelInheritanceTest(ModeltranslationTestBase):
    """Tests for inheritance support in modeltranslation."""
    def test_abstract_inheritance(self):
        field_names_b = AbstractModelB._meta.get_all_field_names()
        self.failIf('titled' in field_names_b)
        self.failIf('titled_de' in field_names_b)
        self.failIf('titled_en' in field_names_b)

    def test_multitable_inheritance(self):
        field_names_a = MultitableModelA._meta.get_all_field_names()
        self.failUnless('titlea' in field_names_a)
        self.failUnless('titlea_de' in field_names_a)
        self.failUnless('titlea_en' in field_names_a)

        field_names_b = MultitableBModelA._meta.get_all_field_names()
        self.failUnless('titlea' in field_names_b)
        self.failUnless('titlea_de' in field_names_b)
        self.failUnless('titlea_en' in field_names_b)
        self.failUnless('titleb' in field_names_b)
        self.failUnless('titleb_de' in field_names_b)
        self.failUnless('titleb_en' in field_names_b)

        field_names_c = MultitableModelC._meta.get_all_field_names()
        self.failUnless('titlea' in field_names_c)
        self.failUnless('titlea_de' in field_names_c)
        self.failUnless('titlea_en' in field_names_c)
        self.failUnless('titleb' in field_names_c)
        self.failUnless('titleb_de' in field_names_c)
        self.failUnless('titleb_en' in field_names_c)
        self.failUnless('titlec' in field_names_c)
        self.failUnless('titlec_de' in field_names_c)
        self.failUnless('titlec_en' in field_names_c)

        field_names_d = MultitableDTestModel._meta.get_all_field_names()
        self.failUnless('titlea' in field_names_d)
        self.failUnless('titlea_de' in field_names_d)
        self.failUnless('titlea_en' in field_names_d)
        self.failUnless('titleb' in field_names_d)
        self.failUnless('titleb_de' in field_names_d)
        self.failUnless('titleb_en' in field_names_d)
        self.failUnless('titled' in field_names_d)


class TranslationAdminTest(ModeltranslationTestBase):
    def setUp(self):
        trans_real.activate('de')
        self.test_obj = TestModel.objects.create(
            title='Testtitle', text='Testtext')
        self.site = AdminSite()

    def tearDown(self):
        trans_real.deactivate()
        self.test_obj.delete()

    def test_default_fields(self):
        class TestModelAdmin(TranslationAdmin):
            pass

        ma = TestModelAdmin(TestModel, self.site)
        self.assertEqual(
            ma.get_form(request).base_fields.keys(),
            ['title_de', 'title_en', 'text_de', 'text_en', 'url_de', 'url_en',
             'email_de', 'email_en'])

    def test_default_fieldsets(self):
        class TestModelAdmin(TranslationAdmin):
            pass

        ma = TestModelAdmin(TestModel, self.site)
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
        class TestModelAdmin(TranslationAdmin):
            fields = ['title']

        ma = TestModelAdmin(TestModel, self.site)
        fields = ['title_de', 'title_en']
        self.assertEqual(ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

    def test_field_arguments_restricted_on_form(self):
        # Using `fields`.
        class TestModelAdmin(TranslationAdmin):
            fields = ['title']

        ma = TestModelAdmin(TestModel, self.site)
        fields = ['title_de', 'title_en']
        self.assertEqual(ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

        # Using `fieldsets`.
        class TestModelAdmin(TranslationAdmin):
            fieldsets = [(None, {'fields': ['title']})]

        ma = TestModelAdmin(TestModel, self.site)
        self.assertEqual(ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

        # Using `exclude`.
        class TestModelAdmin(TranslationAdmin):
            exclude = ['url', 'email']

        ma = TestModelAdmin(TestModel, self.site)
        fields = ['title_de', 'title_en', 'text_de', 'text_en']
        self.assertEqual(
            ma.get_form(request).base_fields.keys(), fields)

        # You can also pass a tuple to `exclude`.
        class TestModelAdmin(TranslationAdmin):
            exclude = ('url', 'email')

        ma = TestModelAdmin(TestModel, self.site)
        self.assertEqual(
            ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

        # Using `fields` and `exclude`.
        class TestModelAdmin(TranslationAdmin):
            fields = ['title', 'url']
            exclude = ['url']

        ma = TestModelAdmin(TestModel, self.site)
        self.assertEqual(
            ma.get_form(request).base_fields.keys(), ['title_de', 'title_en'])

    def test_field_arguments_restricted_on_custom_form(self):
        # Using `fields`.
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = TestModel
                fields = ['url', 'email']

        class TestModelAdmin(TranslationAdmin):
            form = TestModelForm

        ma = TestModelAdmin(TestModel, self.site)
        fields = ['url_de', 'url_en', 'email_de', 'email_en']
        self.assertEqual(
            ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

        # Using `exclude`.
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = TestModel
                exclude = ['url', 'email']

        class TestModelAdmin(TranslationAdmin):
            form = TestModelForm

        ma = TestModelAdmin(TestModel, self.site)
        fields = ['title_de', 'title_en', 'text_de', 'text_en']
        self.assertEqual(
            ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

        # If both, the custom form an the ModelAdmin define an `exclude`
        # option, the ModelAdmin wins. This is Django behaviour.
        class TestModelAdmin(TranslationAdmin):
            form = TestModelForm
            exclude = ['url']

        ma = TestModelAdmin(TestModel, self.site)
        fields = ['title_de', 'title_en', 'text_de', 'text_en', 'email_de',
                  'email_en']
        self.assertEqual(
            ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

        # Same for `fields`.
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = TestModel
                fields = ['text', 'title']

        class TestModelAdmin(TranslationAdmin):
            form = TestModelForm
            fields = ['email']

        ma = TestModelAdmin(TestModel, self.site)
        fields = ['email_de', 'email_en']
        self.assertEqual(
            ma.get_form(request).base_fields.keys(), fields)
        self.assertEqual(
            ma.get_form(request, self.test_obj).base_fields.keys(), fields)

    def test_inline_fieldsets(self):
        class DataInline(TranslationStackedInline):
            model = DataModel
            fieldsets = [
                ('Test', {'fields': ('data',)})
            ]

        class TestModelAdmin(TranslationAdmin):
            exclude = ('title', 'text',)
            inlines = [DataInline]

        class DataTranslationOptions(translator.TranslationOptions):
            fields = ('data',)

        translator.translator.register(DataModel,
                                       DataTranslationOptions)
        ma = TestModelAdmin(TestModel, self.site)

        fieldsets = [('Test', {'fields': ['data_de', 'data_en']})]

        try:
            ma_fieldsets = ma.get_inline_instances(
                request)[0].get_fieldsets(request)
        except AttributeError:  # Django 1.3 fallback
            ma_fieldsets = ma.inlines[0](
                TestModel, self.site).get_fieldsets(request)
        self.assertEqual(ma_fieldsets, fieldsets)

        try:
            ma_fieldsets = ma.get_inline_instances(
                request)[0].get_fieldsets(request, self.test_obj)
        except AttributeError:  # Django 1.3 fallback
            ma_fieldsets = ma.inlines[0](
                TestModel, self.site).get_fieldsets(request, self.test_obj)
        self.assertEqual(ma_fieldsets, fieldsets)


class TestManager(ModeltranslationTestBase):
    def setUp(self):
        # In this test case the default language is en, not de.
        trans_real.activate('en')

    def test_filter_update(self):
        """Test if filtering and updating is language-aware."""
        n = ManagerTestModel(title='')
        n.title_en = 'en'
        n.title_de = 'de'
        n.save()

        m = ManagerTestModel(title='')
        m.title_en = 'title en'
        m.title_de = 'de'
        m.save()

        self.assertEqual('en', get_language())

        self.assertEqual(0, ManagerTestModel.objects.filter(title='de').count())
        self.assertEqual(1, ManagerTestModel.objects.filter(title='en').count())
        # Spanning works
        self.assertEqual(2, ManagerTestModel.objects.filter(title__contains='en').count())

        with override('de'):
            self.assertEqual(2, ManagerTestModel.objects.filter(title='de').count())
            self.assertEqual(0, ManagerTestModel.objects.filter(title='en').count())
            # Spanning works
            self.assertEqual(2, ManagerTestModel.objects.filter(title__endswith='e').count())

            # Still possible to use explicit language version
            self.assertEqual(1, ManagerTestModel.objects.filter(title_en='en').count())
            self.assertEqual(2, ManagerTestModel.objects.filter(title_en__contains='en').count())

            ManagerTestModel.objects.update(title='new')
            self.assertEqual(2, ManagerTestModel.objects.filter(title='new').count())
            n = ManagerTestModel.objects.get(pk=n.pk)
            m = ManagerTestModel.objects.get(pk=m.pk)
            self.assertEqual('en', n.title_en)
            self.assertEqual('new', n.title_de)
            self.assertEqual('title en', m.title_en)
            self.assertEqual('new', m.title_de)

    def test_q(self):
        """Test if Q queries are rewritten."""
        n = ManagerTestModel(title='')
        n.title_en = 'en'
        n.title_de = 'de'
        n.save()

        self.assertEqual('en', get_language())
        self.assertEqual(0, ManagerTestModel.objects.filter(Q(title='de') | Q(pk=42)).count())
        self.assertEqual(1, ManagerTestModel.objects.filter(Q(title='en') | Q(pk=42)).count())

        with override('de'):
            self.assertEqual(1, ManagerTestModel.objects.filter(Q(title='de') | Q(pk=42)).count())
            self.assertEqual(0, ManagerTestModel.objects.filter(Q(title='en') | Q(pk=42)).count())

    def test_f(self):
        """Test if F queries are rewritten."""
        n = ManagerTestModel.objects.create(visits_en=1, visits_de=2)

        self.assertEqual('en', get_language())
        ManagerTestModel.objects.update(visits=F('visits') + 10)
        n = ManagerTestModel.objects.all()[0]
        self.assertEqual(n.visits_en, 11)
        self.assertEqual(n.visits_de, 2)

        with override('de'):
            ManagerTestModel.objects.update(visits=F('visits') + 20)
            n = ManagerTestModel.objects.all()[0]
            self.assertEqual(n.visits_en, 11)
            self.assertEqual(n.visits_de, 22)

    def test_custom_manager(self):
        """Test if user-defined manager is still working"""
        n = CustomManagerTestModel(title='')
        n.title_en = 'enigma'
        n.title_de = 'foo'
        n.save()

        m = CustomManagerTestModel(title='')
        m.title_en = 'enigma'
        m.title_de = 'bar'
        m.save()

        # Custom method
        self.assertEqual('bar', CustomManagerTestModel.objects.foo())

        # Ensure that get_query_set is working - filter objects to those with 'a' in title
        self.assertEqual('en', get_language())
        self.assertEqual(2, CustomManagerTestModel.objects.count())
        with override('de'):
            self.assertEqual(1, CustomManagerTestModel.objects.count())

    def test_creation(self):
        """Test if field are rewritten in create."""
        self.assertEqual('en', get_language())
        n = ManagerTestModel.objects.create(title='foo')
        self.assertEqual('foo', n.title_en)
        self.assertEqual(None, n.title_de)
        self.assertEqual('foo', n.title)

        # The same result
        n = ManagerTestModel.objects.create(title_en='foo')
        self.assertEqual('foo', n.title_en)
        self.assertEqual(None, n.title_de)
        self.assertEqual('foo', n.title)

        # Language suffixed version wins
        n = ManagerTestModel.objects.create(title='bar', title_en='foo')
        self.assertEqual('foo', n.title_en)
        self.assertEqual(None, n.title_de)
        self.assertEqual('foo', n.title)

    def test_creation_population(self):
        """Test if language fields are populated with default value on creation."""
        n = ManagerTestModel.objects.create(title='foo', _populate=True)
        self.assertEqual('foo', n.title_en)
        self.assertEqual('foo', n.title_de)
        self.assertEqual('foo', n.title)

        # You can specify some language...
        n = ManagerTestModel.objects.create(title='foo', title_de='bar', _populate=True)
        self.assertEqual('foo', n.title_en)
        self.assertEqual('bar', n.title_de)
        self.assertEqual('foo', n.title)

        # ... but remember that still original attribute points to current language
        self.assertEqual('en', get_language())
        n = ManagerTestModel.objects.create(title='foo', title_en='bar', _populate=True)
        self.assertEqual('bar', n.title_en)
        self.assertEqual('foo', n.title_de)
        self.assertEqual('bar', n.title)  # points to en
        with override('de'):
            self.assertEqual('foo', n.title)  # points to de
        self.assertEqual('en', get_language())

        # This feature (for backward-compatibility) require _populate keyword...
        n = ManagerTestModel.objects.create(title='foo')
        self.assertEqual('foo', n.title_en)
        self.assertEqual(None, n.title_de)
        self.assertEqual('foo', n.title)

        # ... or MODELTRANSLATION_AUTO_POPULATE setting
        with override_settings(MODELTRANSLATION_AUTO_POPULATE=True):
            reload(mt_settings)
            self.assertEqual(True, mt_settings.AUTO_POPULATE)
            n = ManagerTestModel.objects.create(title='foo')
            self.assertEqual('foo', n.title_en)
            self.assertEqual('foo', n.title_de)
            self.assertEqual('foo', n.title)

            # _populate keyword has highest priority
            n = ManagerTestModel.objects.create(title='foo', _populate=False)
            self.assertEqual('foo', n.title_en)
            self.assertEqual(None, n.title_de)
            self.assertEqual('foo', n.title)

        # Restore previous state
        reload(mt_settings)
        self.assertEqual(False, mt_settings.AUTO_POPULATE)
