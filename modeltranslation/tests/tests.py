# -*- coding: utf-8 -*-
from decimal import Decimal
from unittest import skipUnless
import datetime
import fnmatch
import imp
import io
import os
import shutil

import django
import six
from django import forms
from django.conf import settings as django_settings
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.db.models import Q, F, Count, TextField
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils.translation import get_language, override, trans_real

from django.apps import apps as django_apps

from modeltranslation import admin, settings as mt_settings, translator
from modeltranslation.forms import TranslationModelForm
from modeltranslation.manager import MultilingualManager
from modeltranslation.models import autodiscover
from modeltranslation.tests.test_settings import TEST_SETTINGS
from modeltranslation.utils import (build_css_class, build_localized_fieldname,
                                    auto_populate, fallbacks)

MIGRATIONS = "django.contrib.auth" in TEST_SETTINGS['INSTALLED_APPS']

models = translation = None

# None of the following tests really depend on the content of the request,
# so we'll just pass in None.
request = None

# How many models are registered for tests.
TEST_MODELS = 35 + (1 if MIGRATIONS else 0)


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


def get_field_names(model):
    names = set()
    fields = model._meta.get_fields()
    for field in fields:
        if field.is_relation and field.many_to_one and field.related_model is None:
            continue
        if field.model != model and field.model._meta.concrete_model == model._meta.concrete_model:
            continue

        names.add(field.name)
        if hasattr(field, 'attname'):
            names.add(field.attname)
    return names


@override_settings(**TEST_SETTINGS)
class ModeltranslationTransactionTestBase(TransactionTestCase):
    cache = django_apps
    synced = False

    @classmethod
    def _get_migrations_path(cls):
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "auth_migrations"
        )

    @classmethod
    def _copy_migrations(cls):
        # Locate the original contrib.auth migrations files
        import django.contrib.auth.migrations as auth_migrations
        source_dir_path = os.path.dirname(auth_migrations.__file__)

        # Copy them to the local auth_migrations directory
        target_dir_path = cls._get_migrations_path()
        for f in os.listdir(source_dir_path):
            source_path = os.path.join(source_dir_path, f)
            target_path = os.path.join(target_dir_path, f)

            # Only migration files get copied
            if os.path.isfile(source_path) and not fnmatch.fnmatch(
                    f, "__init__.py"
            ):
                shutil.copyfile(source_path, target_path)

    @classmethod
    def _clean_migrations(cls):
        target_dir_path = cls._get_migrations_path()
        for f in os.listdir(target_dir_path):
            target_path = os.path.join(target_dir_path, f)
            if os.path.isfile(target_path) and not fnmatch.fnmatch(
                    f, "__init__.py"):
                os.remove(target_path)

    @classmethod
    def setUpClass(cls):
        """
        Prepare database:
        * Call syncdb to create tables for tests.models (since during
        default testrunner's db creation modeltranslation.tests was not in INSTALLED_APPS
        """
        super(ModeltranslationTransactionTestBase, cls).setUpClass()
        if not ModeltranslationTransactionTestBase.synced:
            # In order to perform only one syncdb
            ModeltranslationTransactionTestBase.synced = True
            # 0. Render initial migration of auth
            if MIGRATIONS:
                # Make copies of auth migrations in the (local) auth_migrations
                # module to setup test database
                cls._copy_migrations()
                call_command('makemigrations', 'auth', verbosity=2, interactive=False)

            # 1. Reload translation in case USE_I18N was False
            from django.utils import translation as dj_trans
            imp.reload(dj_trans)

            # 2. Reload MT because LANGUAGES likely changed.
            imp.reload(mt_settings)
            imp.reload(translator)
            imp.reload(admin)

            # 3. Reset test models (because autodiscover have already run, those models
            #    have translation fields, but for languages previously defined. We want
            #    to be sure that 'de' and 'en' are available)
            del cls.cache.all_models['tests']
            if MIGRATIONS:
                del cls.cache.all_models['auth']
            import sys
            sys.modules.pop('modeltranslation.tests.models', None)
            sys.modules.pop('modeltranslation.tests.translation', None)
            if MIGRATIONS:
                sys.modules.pop('django.contrib.auth.models', None)
            cls.cache.get_app_config('tests').import_models()
            if MIGRATIONS:
                cls.cache.get_app_config('auth').import_models()

            # 4. Autodiscover
            from modeltranslation.models import handle_translation_registrations
            handle_translation_registrations()

            # 5. makemigrations (``migrate=False`` in case of south)
            if MIGRATIONS:
                call_command('makemigrations', 'auth', verbosity=2, interactive=False)
                # At this point there should not be any migrations to generate
                out = io.StringIO()
                call_command('makemigrations', 'auth', verbosity=3,
                             dry_run=True, interactive=False, stdout=out)
                assert "No changes detected in app 'auth'\n" == out.getvalue(), \
                    "Unexpected auth migration:\n %s" % out.getvalue()

            # 6. Syncdb (``migrate=False`` in case of south)
            call_command('migrate', verbosity=0, interactive=False, run_syncdb=True)

            # 7. clean migrations
            if MIGRATIONS:
                cls._clean_migrations()

            # A rather dirty trick to import models into module namespace, but not before
            # tests app has been added into INSTALLED_APPS and loaded
            # (that's why this is not imported in normal import section)
            global models, translation
            from modeltranslation.tests import models, translation  # NOQA

    def setUp(self):
        self._old_language = get_language()
        trans_real.activate('de')

    def tearDown(self):
        trans_real.activate(self._old_language)


class ModeltranslationTestBase(TestCase, ModeltranslationTransactionTestBase):
    pass


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
        del self.cache.all_models['test_app']
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
        langs = tuple(val for val, label in django_settings.LANGUAGES)
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
                          translator.translator.get_options_for_model, models.ThirdPartyModel)

        # Ensure that a base can't be registered after a subclass.
        self.assertRaises(translator.DescendantRegistered,
                          translator.translator.register, models.BasePage)

        # Or unregistered before it.
        self.assertRaises(translator.DescendantRegistered,
                          translator.translator.unregister, models.Slugged)

    def test_registration_field_conflicts(self):
        before = len(translator.translator.get_registered_models())

        # Exception should be raised when conflicting field name detected
        self.assertRaises(ValueError, translator.translator.register,
                          models.ConflictModel, fields=('title',))
        self.assertRaises(ValueError, translator.translator.register,
                          models.AbstractConflictModelB, fields=('title',))
        self.assertRaises(ValueError, translator.translator.register,
                          models.MultitableConflictModelB, fields=('title',))

        # Model should not be registered
        self.assertEqual(len(translator.translator.get_registered_models()), before)

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
        self.assertEqual(six.text_type(verbose_name), 'title [de]')

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
            translation.FallbackModel2TranslationOptions.fallback_values['text'])

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


class ModeltranslationTransactionTest(ModeltranslationTransactionTestBase):
    def test_unique_nullable_field(self):
        from django.db import transaction
        models.UniqueNullableModel.objects.create()
        models.UniqueNullableModel.objects.create()
        models.UniqueNullableModel.objects.create(title=None)
        models.UniqueNullableModel.objects.create(title=None)

        models.UniqueNullableModel.objects.create(title='')
        self.assertRaises(IntegrityError, models.UniqueNullableModel.objects.create, title='')
        transaction.rollback()  # Postgres
        models.UniqueNullableModel.objects.create(title='foo')
        self.assertRaises(IntegrityError, models.UniqueNullableModel.objects.create, title='foo')
        transaction.rollback()  # Postgres


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

    def test_fallback_undefined(self):
        """
        Checks if a sensible value is considered undefined and triggers
        fallbacks. Tests if the value can be overridden as documented.
        """
        with reload_override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=self.test_fallback):
            # Non-nullable CharField falls back on empty strings.
            m = models.FallbackModel(title_en='value', title_de='')
            with override('en'):
                self.assertEqual(m.title, 'value')
            with override('de'):
                self.assertEqual(m.title, 'value')

            # Nullable CharField does not fall back on empty strings.
            m = models.FallbackModel(description_en='value', description_de='')
            with override('en'):
                self.assertEqual(m.description, 'value')
            with override('de'):
                self.assertEqual(m.description, '')

            # Nullable CharField does fall back on None.
            m = models.FallbackModel(description_en='value', description_de=None)
            with override('en'):
                self.assertEqual(m.description, 'value')
            with override('de'):
                self.assertEqual(m.description, 'value')

            # The undefined value may be overridden.
            m = models.FallbackModel2(title_en='value', title_de='')
            with override('en'):
                self.assertEqual(m.title, 'value')
            with override('de'):
                self.assertEqual(m.title, '')
            m = models.FallbackModel2(title_en='value', title_de='no title')
            with override('en'):
                self.assertEqual(m.title, 'value')
            with override('de'):
                self.assertEqual(m.title, 'value')


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
        self.assertTrue(default_storage.exists(inst.file.path))
        self.assertTrue(inst.file.size > 0)
        self.assertTrue(default_storage.exists(inst.image.path))
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

    def test_empty_field(self):
        from django.db.models.fields.files import FieldFile
        inst = models.FileFieldsModel()
        self.assertIsInstance(inst.file, FieldFile)
        self.assertIsInstance(inst.file2, FieldFile)
        inst.save()
        inst = models.FileFieldsModel.objects.all()[0]
        self.assertIsInstance(inst.file, FieldFile)
        self.assertIsInstance(inst.file2, FieldFile)

    def test_fallback(self):
        from django.db.models.fields.files import FieldFile
        with reload_override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=('en',)):
            self.assertEqual(get_language(), 'de')
            inst = models.FileFieldsModel()
            inst.file_de = ''
            inst.file_en = 'foo'
            inst.file2_de = ''
            inst.file2_en = 'bar'
            self.assertIsInstance(inst.file, FieldFile)
            self.assertIsInstance(inst.file2, FieldFile)
            self.assertEqual(inst.file.name, 'foo')
            self.assertEqual(inst.file2.name, 'bar')
            inst.save()
            inst = models.FileFieldsModel.objects.all()[0]
            self.assertIsInstance(inst.file, FieldFile)
            self.assertIsInstance(inst.file2, FieldFile)
            self.assertEqual(inst.file.name, 'foo')
            self.assertEqual(inst.file2.name, 'bar')


class ForeignKeyFieldsTest(ModeltranslationTestBase):
    @classmethod
    def setUpClass(cls):
        # 'model' attribute cannot be assigned to class in its definition,
        # because ``models`` module will be reloaded and hence class would use old model classes.
        super(ForeignKeyFieldsTest, cls).setUpClass()
        cls.model = models.ForeignKeyModel

    def test_translated_models(self):
        field_names = dir(self.model())
        self.assertTrue('id' in field_names)
        for f in ('test', 'test_de', 'test_en', 'optional', 'optional_en', 'optional_de'):
            self.assertTrue(f in field_names)
            self.assertTrue('%s_id' % f in field_names)

    def test_db_column_names(self):
        meta = self.model._meta

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
        inst = self.model()

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

        # Test caching
        inst.test_en = test_inst2
        inst.save()
        trans_real.activate("de")
        self.assertEqual(inst.test, test_inst1)
        trans_real.activate("en")
        self.assertEqual(inst.test, test_inst2)

        # Check filtering in direct way + lookup spanning
        manager = self.model.objects
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
        fk_inst_both = self.model(title_en='f_title_en', title_de='f_title_de',
                                  test_de=test_inst, test_en=test_inst)
        fk_inst_both.save()
        fk_inst_de = self.model(title_en='f_title_en', title_de='f_title_de',
                                test_de_id=test_inst.pk)
        fk_inst_de.save()
        fk_inst_en = self.model(title_en='f_title_en', title_de='f_title_de',
                                test_en=test_inst)
        fk_inst_en.save()

        fk_option_de = self.model.objects.create(optional_de=test_inst)
        fk_option_en = self.model.objects.create(optional_en=test_inst)

        # Check that the reverse accessors are created on the model:
        # Explicit related_name
        testmodel_fields = get_field_names(models.TestModel)
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
        test_inst2.test_fks.set((fk_inst_de, fk_inst_both))
        test_inst2.test_fks_en.set((fk_inst_en, fk_inst_both))

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

    def test_reverse_lookup_with_filtered_queryset_manager(self):
        """
        Make sure base_manager does not get same queryset filter as TestModel in reverse lookup
        https://docs.djangoproject.com/en/3.0/topics/db/managers/#base-managers
        """
        from modeltranslation.tests.models import FilteredManager

        test_inst = models.FilteredTestModel(title_en='title_en', title_de='title_de')
        test_inst.save()

        self.assertFalse(models.FilteredTestModel.objects.all().exists())
        self.assertEqual(models.FilteredTestModel.objects.__class__, FilteredManager)
        self.assertEqual(models.FilteredTestModel._meta.base_manager.__class__, MultilingualManager)

        # # create objects with relations to test_inst
        fk_inst = models.ForeignKeyFilteredModel(test=test_inst,
                                                 title_en='f_title_en', title_de='f_title_de')
        fk_inst.save()
        fk_inst.refresh_from_db()   # force to reset cached values

        self.assertEqual(models.ForeignKeyFilteredModel.objects.__class__, MultilingualManager)
        self.assertEqual(models.ForeignKeyFilteredModel._meta.base_manager.__class__,
                         MultilingualManager)
        self.assertEqual(fk_inst.test, test_inst)

    def test_non_translated_relation(self):
        non_de = models.NonTranslated.objects.create(title='title_de')
        non_en = models.NonTranslated.objects.create(title='title_en')

        fk_inst_both = self.model.objects.create(
            title_en='f_title_en', title_de='f_title_de', non_de=non_de, non_en=non_en)
        fk_inst_de = self.model.objects.create(non_de=non_de)
        fk_inst_en = self.model.objects.create(non_en=non_en)

        # Forward relation + spanning
        manager = self.model.objects
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

    def test_indonesian(self):
        field = models.ForeignKeyModel._meta.get_field('test')
        self.assertNotEqual(field.attname, build_localized_fieldname(field.name, 'id'))

    def assertQuerysetsEqual(self, qs1, qs2):
        def pk(o):
            return o.pk

        return self.assertEqual(sorted(qs1, key=pk), sorted(qs2, key=pk))


class OneToOneFieldsTest(ForeignKeyFieldsTest):
    @classmethod
    def setUpClass(cls):
        # 'model' attribute cannot be assigned to class in its definition,
        # because ``models`` module will be reloaded and hence class would use old model classes.
        super(OneToOneFieldsTest, cls).setUpClass()
        cls.model = models.OneToOneFieldModel

    def test_uniqueness(self):
        test_inst1 = models.TestModel(title_en='title1_en', title_de='title1_de')
        test_inst1.save()
        inst = self.model()

        trans_real.activate("de")
        inst.test = test_inst1

        trans_real.activate("en")
        # That's ok, since test_en is different than test_de
        inst.test = test_inst1
        inst.save()

        # But this violates uniqueness constraint
        inst2 = self.model(test=test_inst1)
        self.assertRaises(IntegrityError, inst2.save)

    def test_reverse_relations(self):
        test_inst = models.TestModel(title_en='title_en', title_de='title_de')
        test_inst.save()

        # Instantiate many 'OneToOneFieldModel' instances:
        fk_inst_de = self.model(title_en='f_title_en', title_de='f_title_de',
                                test_de_id=test_inst.pk)
        fk_inst_de.save()
        fk_inst_en = self.model(title_en='f_title_en', title_de='f_title_de',
                                test_en=test_inst)
        fk_inst_en.save()

        fk_option_de = self.model.objects.create(optional_de=test_inst)
        fk_option_en = self.model.objects.create(optional_en=test_inst)

        # Check that the reverse accessors are created on the model:
        # Explicit related_name
        testmodel_fields = get_field_names(models.TestModel)
        testmodel_methods = dir(models.TestModel)
        self.assertIn('test_o2o',    testmodel_fields)
        self.assertIn('test_o2o_de', testmodel_fields)
        self.assertIn('test_o2o_en', testmodel_fields)
        self.assertIn('test_o2o',    testmodel_methods)
        self.assertIn('test_o2o_de', testmodel_methods)
        self.assertIn('test_o2o_en', testmodel_methods)
        # Implicit related_name
        self.assertIn('onetoonefieldmodel',    testmodel_fields)
        self.assertIn('onetoonefieldmodel_de', testmodel_fields)
        self.assertIn('onetoonefieldmodel_en', testmodel_fields)
        self.assertIn('onetoonefieldmodel',    testmodel_methods)
        self.assertIn('onetoonefieldmodel_de', testmodel_methods)
        self.assertIn('onetoonefieldmodel_en', testmodel_methods)

        # Check the German reverse accessor:
        self.assertEqual(fk_inst_de, test_inst.test_o2o_de)

        # Check the English reverse accessor:
        self.assertEqual(fk_inst_en, test_inst.test_o2o_en)

        # Check the default reverse accessor:
        trans_real.activate("de")
        self.assertEqual(fk_inst_de, test_inst.test_o2o)
        trans_real.activate("en")
        self.assertEqual(fk_inst_en, test_inst.test_o2o)

        # Check implicit related_name reverse accessor:
        self.assertEqual(fk_option_en, test_inst.onetoonefieldmodel)

        # Check filtering in reverse way + lookup spanning:
        manager = models.TestModel.objects
        trans_real.activate("de")
        self.assertEqual(manager.filter(test_o2o=fk_inst_de).count(), 1)
        self.assertEqual(manager.filter(test_o2o__id=fk_inst_de.pk).count(), 1)
        self.assertEqual(manager.filter(test_o2o=fk_inst_en).count(), 0)
        self.assertEqual(manager.filter(test_o2o_en=fk_inst_en).count(), 1)
        self.assertEqual(manager.filter(onetoonefieldmodel=fk_option_de).count(), 1)
        self.assertEqual(manager.filter(onetoonefieldmodel=fk_option_en).count(), 0)
        self.assertEqual(manager.filter(onetoonefieldmodel_en=fk_option_en).count(), 1)
        self.assertEqual(manager.filter(test_o2o__title='f_title_de').distinct().count(), 1)
        self.assertEqual(manager.filter(test_o2o__title='f_title_en').distinct().count(), 0)
        self.assertEqual(manager.filter(test_o2o__title_en='f_title_en').distinct().count(), 1)
        trans_real.activate("en")
        self.assertEqual(manager.filter(test_o2o=fk_inst_en).count(), 1)
        self.assertEqual(manager.filter(test_o2o__id=fk_inst_en.pk).count(), 1)
        self.assertEqual(manager.filter(test_o2o=fk_inst_de).count(), 0)
        self.assertEqual(manager.filter(test_o2o_de=fk_inst_de).count(), 1)
        self.assertEqual(manager.filter(onetoonefieldmodel=fk_option_en).count(), 1)
        self.assertEqual(manager.filter(onetoonefieldmodel=fk_option_de).count(), 0)
        self.assertEqual(manager.filter(onetoonefieldmodel_de=fk_option_de).count(), 1)
        self.assertEqual(manager.filter(test_o2o__title='f_title_en').distinct().count(), 1)
        self.assertEqual(manager.filter(test_o2o__title='f_title_de').distinct().count(), 0)
        self.assertEqual(manager.filter(test_o2o__title_de='f_title_de').distinct().count(), 1)

        # Check assignment
        trans_real.activate("de")
        test_inst2 = models.TestModel(title_en='title_en', title_de='title_de')
        test_inst2.save()
        test_inst2.test_o2o = fk_inst_de
        test_inst2.test_o2o_en = fk_inst_en

        self.assertEqual(fk_inst_de.test.pk, test_inst2.pk)
        self.assertEqual(fk_inst_de.test_id, test_inst2.pk)
        self.assertEqual(fk_inst_de.test_de, test_inst2)
        self.assertEqual(test_inst2.test_o2o_de, test_inst2.test_o2o)
        self.assertEqual(fk_inst_de, test_inst2.test_o2o)
        trans_real.activate("en")
        self.assertEqual(fk_inst_en.test.pk, test_inst2.pk)
        self.assertEqual(fk_inst_en.test_id, test_inst2.pk)
        self.assertEqual(fk_inst_en.test_en, test_inst2)
        self.assertEqual(test_inst2.test_o2o_en, test_inst2.test_o2o)
        self.assertEqual(fk_inst_en, test_inst2.test_o2o)

    def test_non_translated_relation(self):
        non_de = models.NonTranslated.objects.create(title='title_de')
        non_en = models.NonTranslated.objects.create(title='title_en')

        fk_inst_de = self.model.objects.create(
            title_en='f_title_en', title_de='f_title_de', non_de=non_de)
        fk_inst_en = self.model.objects.create(
            title_en='f_title_en2', title_de='f_title_de2', non_en=non_en)

        # Forward relation + spanning
        manager = self.model.objects
        trans_real.activate("de")
        self.assertEqual(manager.filter(non=non_de).count(), 1)
        self.assertEqual(manager.filter(non=non_en).count(), 0)
        self.assertEqual(manager.filter(non_en=non_en).count(), 1)
        self.assertEqual(manager.filter(non__title='title_de').count(), 1)
        self.assertEqual(manager.filter(non__title='title_en').count(), 0)
        self.assertEqual(manager.filter(non_en__title='title_en').count(), 1)
        trans_real.activate("en")
        self.assertEqual(manager.filter(non=non_en).count(), 1)
        self.assertEqual(manager.filter(non=non_de).count(), 0)
        self.assertEqual(manager.filter(non_de=non_de).count(), 1)
        self.assertEqual(manager.filter(non__title='title_en').count(), 1)
        self.assertEqual(manager.filter(non__title='title_de').count(), 0)
        self.assertEqual(manager.filter(non_de__title='title_de').count(), 1)

        # Reverse relation + spanning
        manager = models.NonTranslated.objects
        trans_real.activate("de")
        self.assertEqual(manager.filter(test_o2o=fk_inst_de).count(), 1)
        self.assertEqual(manager.filter(test_o2o=fk_inst_en).count(), 0)
        self.assertEqual(manager.filter(test_o2o_en=fk_inst_en).count(), 1)
        self.assertEqual(manager.filter(test_o2o__title='f_title_de').count(), 1)
        self.assertEqual(manager.filter(test_o2o__title='f_title_en').count(), 0)
        self.assertEqual(manager.filter(test_o2o__title_en='f_title_en').count(), 1)
        trans_real.activate("en")
        self.assertEqual(manager.filter(test_o2o=fk_inst_en).count(), 1)
        self.assertEqual(manager.filter(test_o2o=fk_inst_de).count(), 0)
        self.assertEqual(manager.filter(test_o2o_de=fk_inst_de).count(), 1)
        self.assertEqual(manager.filter(test_o2o__title='f_title_en2').count(), 1)
        self.assertEqual(manager.filter(test_o2o__title='f_title_de2').count(), 0)
        self.assertEqual(manager.filter(test_o2o__title_de='f_title_de2').count(), 1)


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
        self.assertTrue('genericip' in field_names)
        self.assertTrue('genericip_de' in field_names)
        self.assertTrue('genericip_en' in field_names)
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

    def test_translated_models_genericipaddress_instance(self):
        inst = models.OtherFieldsModel()
        inst.genericip = '2a02:42fe::4'
        self.assertEqual('de', get_language())
        self.assertEqual('2a02:42fe::4', inst.genericip)
        self.assertEqual('2a02:42fe::4', inst.genericip_de)
        self.assertEqual(None, inst.genericip_en)

        inst.genericip = '2a02:23fe::4'
        inst.save()
        self.assertEqual('2a02:23fe::4', inst.genericip)
        self.assertEqual('2a02:23fe::4', inst.genericip_de)
        self.assertEqual(None, inst.genericip_en)

        trans_real.activate('en')
        inst.genericip = '2a02:42fe::4'
        self.assertEqual('2a02:42fe::4', inst.genericip)
        self.assertEqual('2a02:23fe::4', inst.genericip_de)
        self.assertEqual('2a02:42fe::4', inst.genericip_en)

        # Check if validation is preserved
        inst.genericip = '1;2'
        self.assertRaises(ValidationError, inst.full_clean)

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

    def test_dates_queryset(self):
        Model = models.OtherFieldsModel

        Model.objects.create(datetime=datetime.datetime(2015, 9, 2, 0, 0))
        Model.objects.create(datetime=datetime.datetime(2014, 8, 3, 0, 0))
        Model.objects.create(datetime=datetime.datetime(2013, 7, 4, 0, 0))

        qs = Model.objects.dates('datetime', 'year', 'DESC')

        self.assertEqual(list(qs), [
            datetime.date(2015, 1, 1),
            datetime.date(2014, 1, 1),
            datetime.date(2013, 1, 1)
        ])

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
        db_values = models.DescriptorModel.objects.raw_values('normal', 'trans_en', 'trans_de')[0]
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
        db_values = models.DescriptorModel.objects.raw_values('normal', 'trans_en', 'trans_de')[0]
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
        field_names_b = get_field_names(models.AbstractModelB)
        self.assertTrue('titlea' in field_names_b)
        self.assertTrue('titlea_de' in field_names_b)
        self.assertTrue('titlea_en' in field_names_b)
        self.assertTrue('titleb' in field_names_b)
        self.assertTrue('titleb_de' in field_names_b)
        self.assertTrue('titleb_en' in field_names_b)
        self.assertFalse('titled' in field_names_b)
        self.assertFalse('titled_de' in field_names_b)
        self.assertFalse('titled_en' in field_names_b)

    def test_multitable_inheritance(self):
        field_names_a = get_field_names(models.MultitableModelA)
        self.assertTrue('titlea' in field_names_a)
        self.assertTrue('titlea_de' in field_names_a)
        self.assertTrue('titlea_en' in field_names_a)

        field_names_b = get_field_names(models.MultitableModelB)
        self.assertTrue('titlea' in field_names_b)
        self.assertTrue('titlea_de' in field_names_b)
        self.assertTrue('titlea_en' in field_names_b)
        self.assertTrue('titleb' in field_names_b)
        self.assertTrue('titleb_de' in field_names_b)
        self.assertTrue('titleb_en' in field_names_b)

        field_names_c = get_field_names(models.MultitableModelC)
        self.assertTrue('titlea' in field_names_c)
        self.assertTrue('titlea_de' in field_names_c)
        self.assertTrue('titlea_en' in field_names_c)
        self.assertTrue('titleb' in field_names_c)
        self.assertTrue('titleb_de' in field_names_c)
        self.assertTrue('titleb_en' in field_names_c)
        self.assertTrue('titlec' in field_names_c)
        self.assertTrue('titlec_de' in field_names_c)
        self.assertTrue('titlec_en' in field_names_c)

        field_names_d = get_field_names(models.MultitableModelD)
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
            model_fields = get_field_names(model)
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
        clsb = translation.FieldInheritanceCTranslationOptions
        self.assertTrue('titlea' in clsb.fields)
        self.assertTrue('titleb' in clsb.fields)
        self.assertTrue('titlec' in clsb.fields)
        self.assertEqual(3, len(clsb.fields))
        self.assertEqual(tuple, type(clsb.fields))

    def test_multi_inheritance(self):
        clsb = translation.FieldInheritanceETranslationOptions
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
        obj1 = models.TestModel.objects.filter(pk=pk1).raw_values()[0]
        obj2 = models.TestModel.objects.filter(pk=pk2).raw_values()[0]
        self.assertEqual('', obj1['title_de'])
        self.assertEqual('initial', obj1['title'])
        self.assertEqual('already', obj2['title_de'])
        self.assertEqual('initial', obj2['title'])

        call_command('update_translation_fields', verbosity=0)

        obj1 = models.TestModel.objects.get(pk=pk1)
        obj2 = models.TestModel.objects.get(pk=pk2)
        self.assertEqual('initial', obj1.title_de)
        self.assertEqual('already', obj2.title_de)

    def test_update_command_language_param(self):
        trans_real.activate('en')
        pk1 = models.TestModel.objects.create(title_en='').pk
        pk2 = models.TestModel.objects.create(title_en='already').pk
        # Due to ``rewrite(False)`` here, original field will be affected.
        models.TestModel.objects.all().rewrite(False).update(title='initial')

        call_command('update_translation_fields', language='en', verbosity=0)

        obj1 = models.TestModel.objects.get(pk=pk1)
        obj2 = models.TestModel.objects.get(pk=pk2)
        self.assertEqual('initial', obj1.title_en)
        self.assertEqual('already', obj2.title_en)

    def test_update_command_invalid_language_param(self):
        with self.assertRaises(CommandError):
            call_command('update_translation_fields', language='xx', verbosity=0)


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

    def test_model_form_widgets(self):
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = models.TestModel
                fields = ['text', ]
                widgets = {
                    'text': forms.Textarea(attrs={'myprop': 'myval'}),
                }

        class TestModelAdmin(admin.TranslationAdmin):
            form = TestModelForm

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ['text_de', 'text_en']
        self.assertEqual(
            tuple(ma.get_form(request).base_fields.keys()), tuple(fields))
        self.assertEqual(
            tuple(ma.get_form(request, self.test_obj).base_fields.keys()), tuple(fields))

        for field in fields:
            self.assertIn(
                'myprop',
                ma.get_form(request).base_fields.get(field).widget.attrs.keys()
            )
            self.assertIn(
                'myval',
                ma.get_form(request, self.test_obj).base_fields.get(field).widget.attrs.values()
            )

    def test_widget_ordering_via_formfield_for_dbfield(self):
        class TestModelAdmin(admin.TranslationAdmin):
            fields = ['text']

            def formfield_for_dbfield(self, db_field, request, **kwargs):
                if isinstance(db_field, TextField):
                    kwargs["widget"] = forms.Textarea(attrs={'myprop': 'myval'})
                    return db_field.formfield(**kwargs)
                return super(TestModelAdmin, self).formfield_for_dbfield(
                    db_field, request, **kwargs
                )

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ['text_de', 'text_en']
        self.assertEqual(
            tuple(ma.get_form(request).base_fields.keys()), tuple(fields))
        self.assertEqual(
            tuple(ma.get_form(request, self.test_obj).base_fields.keys()), tuple(fields))

        for field in fields:
            self.assertIn(
                'myprop',
                ma.get_form(request).base_fields.get(field).widget.attrs.keys()
            )
            self.assertIn(
                'myval',
                ma.get_form(request, self.test_obj).base_fields.get(field).widget.attrs.values()
            )

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

    def test_list_editable(self):
        class TestModelAdmin(admin.TranslationAdmin):
            list_editable = ['title']
            list_display = ['id', 'title']
            list_display_links = ['id']

        ma = TestModelAdmin(models.TestModel, self.site)
        list_editable = ['title_de', 'title_en']
        list_display = ['id', 'title_de', 'title_en']
        self.assertEqual(tuple(ma.list_editable), tuple(list_editable))
        self.assertEqual(tuple(ma.list_display), tuple(list_display))

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
            ('Title', {'classes': ('mt-fieldset',), 'fields': ['title_de', 'title_en']}),
            ('Text', {'classes': ('mt-fieldset',), 'fields': ['text_de', 'text_en']}),
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
            ('Title', {'classes': ('mt-fieldset',), 'fields': ['title_de', 'title_en']}),
            ('Text', {'classes': ('mt-fieldset',), 'fields': ['text_de', 'text_en']}),
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
            ('Title', {'classes': ('mt-fieldset',), 'fields': ['title_de', 'title_en']})
        ]
        self.assertEqual(ma.get_fieldsets(request), fieldsets)
        self.assertEqual(ma.get_fieldsets(request, self.test_obj), fieldsets)

    def test_prepopulated_fields(self):
        trans_real.activate('de')
        self.assertEqual(get_language(), 'de')

        # Non-translated slug based on translated field (using active language)
        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {'slug': ('firstname',)}
        ma = NameModelAdmin(models.NameModel, self.site)
        self.assertEqual(ma.prepopulated_fields, {'slug': ('firstname_de',)})

        # Checking multi-field
        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {'slug': ('firstname', 'lastname',)}
        ma = NameModelAdmin(models.NameModel, self.site)
        self.assertEqual(ma.prepopulated_fields, {'slug': ('firstname_de', 'lastname_de',)})

        # Non-translated slug based on non-translated field (no change)
        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {'slug': ('age',)}
        ma = NameModelAdmin(models.NameModel, self.site)
        self.assertEqual(ma.prepopulated_fields, {'slug': ('age',)})

        # Translated slug based on non-translated field (all populated on the same value)
        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {'slug2': ('age',)}
        ma = NameModelAdmin(models.NameModel, self.site)
        self.assertEqual(ma.prepopulated_fields, {'slug2_en': ('age',), 'slug2_de': ('age',)})

        # Translated slug based on translated field (corresponding)
        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {'slug2': ('firstname',)}
        ma = NameModelAdmin(models.NameModel, self.site)
        self.assertEqual(ma.prepopulated_fields, {'slug2_en': ('firstname_en',),
                                                  'slug2_de': ('firstname_de',)})

        # Check that current active language is used
        trans_real.activate('en')
        self.assertEqual(get_language(), 'en')

        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {'slug': ('firstname',)}
        ma = NameModelAdmin(models.NameModel, self.site)
        self.assertEqual(ma.prepopulated_fields, {'slug': ('firstname_en',)})

        # Prepopulation language can be overriden by MODELTRANSLATION_PREPOPULATE_LANGUAGE
        with reload_override_settings(MODELTRANSLATION_PREPOPULATE_LANGUAGE='de'):
            class NameModelAdmin(admin.TranslationAdmin):
                prepopulated_fields = {'slug': ('firstname',)}
            ma = NameModelAdmin(models.NameModel, self.site)
            self.assertEqual(ma.prepopulated_fields, {'slug': ('firstname_de',)})

    def test_proxymodel_field_argument(self):
        class ProxyTestModelAdmin(admin.TranslationAdmin):
            fields = ['title']

        ma = ProxyTestModelAdmin(models.ProxyTestModel, self.site)
        fields = ['title_de', 'title_en']
        self.assertEqual(tuple(ma.get_form(request).base_fields.keys()), tuple(fields))
        self.assertEqual(
            tuple(ma.get_form(request, self.test_obj).base_fields.keys()), tuple(fields))


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
                fields = '__all__'

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

        # Test Python3 "dictionary changed size during iteration"
        self.assertEqual(1, models.ManagerTestModel.objects.filter(title='en',
                                                                   title_en='en').count())

    def test_q(self):
        """Test if Q queries are rewritten."""
        n = models.ManagerTestModel(title='')
        n.title_en = 'en'
        n.title_de = 'de'
        n.save()

        self.assertEqual('en', get_language())
        self.assertEqual(0, models.ManagerTestModel.objects.filter(Q(title='de') |
                                                                   Q(pk=42)).count())
        self.assertEqual(1, models.ManagerTestModel.objects.filter(Q(title='en') |
                                                                   Q(pk=42)).count())

        with override('de'):
            self.assertEqual(1, models.ManagerTestModel.objects.filter(Q(title='de') |
                                                                       Q(pk=42)).count())
            self.assertEqual(0, models.ManagerTestModel.objects.filter(Q(title='en') |
                                                                       Q(pk=42)).count())

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

    def assert_fallback(self, method, expected1, *args, **kwargs):
        transform = kwargs.pop('transform', lambda x: x)
        expected2 = kwargs.pop('expected_de', expected1)
        with default_fallback():
            # Fallback is ('de',)
            obj = method(*args, **kwargs)[0]
            with override('de'):
                obj2 = method(*args, **kwargs)[0]
        self.assertEqual(transform(obj), expected1)
        self.assertEqual(transform(obj2), expected2)

    def test_values_fallback(self):
        manager = models.ManagerTestModel.objects
        manager.create(title_en='', title_de='de')
        self.assertEqual('en', get_language())

        self.assert_fallback(manager.values, 'de', 'title', transform=lambda x: x['title'])
        self.assert_fallback(manager.values_list, 'de', 'title', flat=True)
        self.assert_fallback(manager.values_list, ('de', '', 'de'), 'title', 'title_en', 'title_de')

        # Settings are taken into account - fallback can be disabled
        with override_settings(MODELTRANSLATION_ENABLE_FALLBACKS=False):
            self.assert_fallback(manager.values, '', 'title', expected_de='de',
                                 transform=lambda x: x['title'])

        # Test fallback values
        manager = models.FallbackModel.objects
        manager.create()

        self.assert_fallback(manager.values, 'fallback', 'title', transform=lambda x: x['title'])
        self.assert_fallback(manager.values_list, ('fallback', 'fallback'), 'title', 'text')

    def test_values(self):
        manager = models.ManagerTestModel.objects
        id1 = manager.create(title_en='en', title_de='de').pk

        raw_obj = manager.raw_values('title')[0]
        obj = manager.values('title')[0]
        with override('de'):
            raw_obj2 = manager.raw_values('title')[0]
            obj2 = manager.values('title')[0]

        # Raw_values returns real database values regardless of current language
        self.assertEqual(raw_obj['title'], raw_obj2['title'])
        # Values present language-aware data, from the moment of retrieval
        self.assertEqual(obj['title'],  'en')
        self.assertEqual(obj2['title'], 'de')

        # Values_list behave similarly
        self.assertEqual(list(manager.values_list('title', flat=True)), ['en'])
        with override('de'):
            self.assertEqual(list(manager.values_list('title', flat=True)), ['de'])

        # One can always turn rewrite off
        a = list(manager.rewrite(False).values_list('title', flat=True))
        with override('de'):
            b = list(manager.rewrite(False).values_list('title', flat=True))
        self.assertEqual(a, b)

        i2 = manager.create(title_en='en2', title_de='de2')
        id2 = i2.pk

        # This is somehow repetitive...
        self.assertEqual('en', get_language())
        self.assertEqual(list(manager.values('title')), [{'title': 'en'}, {'title': 'en2'}])
        with override('de'):
            self.assertEqual(list(manager.values('title')), [{'title': 'de'}, {'title': 'de2'}])

        # When no fields are passed, list all fields in current language.
        self.assertEqual(list(manager.values()), [
            {'id': id1, 'title': 'en', 'visits': 0, 'description': None},
            {'id': id2, 'title': 'en2', 'visits': 0, 'description': None}
        ])
        # Similar for values_list
        self.assertEqual(list(manager.values_list()), [(id1, 'en', 0, None), (id2, 'en2', 0, None)])
        with override('de'):
            self.assertEqual(list(manager.values_list()),
                             [(id1, 'de', 0, None), (id2, 'de2', 0, None)])

        # Raw_values
        self.assertEqual(list(manager.raw_values()), list(manager.rewrite(False).values()))
        i2.delete()
        self.assertEqual(list(manager.raw_values()), [
            {'id': id1, 'title': 'en', 'title_en': 'en', 'title_de': 'de',
             'visits': 0, 'visits_en': 0, 'visits_de': 0,
             'description': None, 'description_en': None, 'description_de': None},
        ])

        # annotation issue (#374)
        self.assertEqual(list(manager.values_list('title', flat=True).annotate(Count('title'))),
                         ['en'])

    def test_values_list_annotation(self):
        models.TestModel(title='foo').save()
        models.TestModel(title='foo').save()
        self.assertEqual(
            list(models.TestModel.objects.all().values_list('title').annotate(Count('id'))),
            [('foo', 2)]
        )

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

    def test_custom_manager_custom_method_name(self):
        """Test if custom method also returns MultilingualQuerySet"""
        from modeltranslation.manager import MultilingualQuerySet
        qs = models.CustomManagerTestModel.objects.custom_qs()
        self.assertIsInstance(qs, MultilingualQuerySet)

    @skipUnless(MIGRATIONS, 'migrations/auth not available')
    def test_3rd_party_custom_manager(self):
        from django.contrib.auth.models import Group, GroupManager
        from modeltranslation.manager import MultilingualManager
        testmodel_fields = get_field_names(Group)
        self.assertIn('name',    testmodel_fields)
        self.assertIn('name_de', testmodel_fields)
        self.assertIn('name_en', testmodel_fields)
        self.assertIn('name_en', testmodel_fields)

        self.assertIsInstance(Group.objects, MultilingualManager)
        self.assertIsInstance(Group.objects, GroupManager)
        self.assertIn('get_by_natural_key', dir(Group.objects))

    def test_multilingual_queryset_pickling(self):
        import pickle
        from modeltranslation.manager import MultilingualQuerySet

        # typical
        models.CustomManagerTestModel.objects.create(title='a')
        qs = models.CustomManagerTestModel.objects.all()
        serialized = pickle.dumps(qs)
        deserialized = pickle.loads(serialized)
        self.assertIsInstance(deserialized, MultilingualQuerySet)
        self.assertListEqual(list(qs), list(deserialized))

        # Generated class
        models.CustomManager2TestModel.objects.create()
        qs = models.CustomManager2TestModel.objects.all()
        serialized = pickle.dumps(qs)
        deserialized = pickle.loads(serialized)
        self.assertIsInstance(deserialized, MultilingualQuerySet)
        self.assertIsInstance(deserialized, models.CustomQuerySet)
        self.assertListEqual(list(qs), list(deserialized))

    def test_non_objects_manager(self):
        """Test if managers other than ``objects`` are patched too"""
        from modeltranslation.manager import MultilingualManager
        manager = models.CustomManagerTestModel.another_mgr_name
        self.assertTrue(isinstance(manager, MultilingualManager))

    def test_default_manager_for_inherited_models_with_custom_manager(self):
        """Test if default manager is still set from local managers"""
        manager = models.CustomManagerChildTestModel._meta.default_manager
        self.assertEqual('objects', manager.name)
        self.assertTrue(isinstance(manager, MultilingualManager))
        self.assertTrue(isinstance(
            models.CustomManagerChildTestModel.translations,
            MultilingualManager))

    def test_default_manager_for_inherited_models(self):
        manager = models.PlainChildTestModel._meta.default_manager
        self.assertEqual('objects', manager.name)
        self.assertTrue(isinstance(models.PlainChildTestModel.translations, MultilingualManager))

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
            call_command('loaddata', 'fixture.json', verbosity=0)
            m = models.TestModel.objects.get()
            self.assertEqual(m.title_en, 'foo')
            self.assertEqual(m.title_de, 'foo')
            self.assertEqual(m.text_en, 'bar')
            self.assertEqual(m.text_de, None)

    def test_fixture_population_via_command(self):
        """
        Test that the loaddata command takes new option.
        """
        call_command('loaddata', 'fixture.json', verbosity=0, populate='required')
        m = models.TestModel.objects.get()
        self.assertEqual(m.title_en, 'foo')
        self.assertEqual(m.title_de, 'foo')
        self.assertEqual(m.text_en, 'bar')
        self.assertEqual(m.text_de, None)

        call_command('loaddata', 'fixture.json', verbosity=0, populate='all')
        m = models.TestModel.objects.get()
        self.assertEqual(m.title_en, 'foo')
        self.assertEqual(m.title_de, 'foo')
        self.assertEqual(m.text_en, 'bar')
        self.assertEqual(m.text_de, 'bar')

        # Test if option overrides current context
        with auto_populate('all'):
            call_command('loaddata', 'fixture.json', verbosity=0, populate=False)
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

    def assertDeferredClass(self, item):
        self.assertTrue(len(item.get_deferred_fields()) > 0)

    def test_deferred(self):
        """
        Check if ``only`` and ``defer`` are working.
        """
        models.TestModel.objects.create(title_de='title_de', title_en='title_en')
        inst = models.TestModel.objects.only('title_en')[0]
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

    def test_deferred_fk(self):
        """
        Check if ``select_related`` is rewritten and also
        if ``only`` and ``defer`` are working with deferred classes
        """
        test = models.TestModel.objects.create(title_de='title_de', title_en='title_en')
        with auto_populate('all'):
            models.ForeignKeyModel.objects.create(test=test)

        item = models.ForeignKeyModel.objects.select_related("test").defer("test__text")[0]
        self.assertDeferredClass(item.test)
        self.assertEqual('title_en', item.test.title)
        self.assertEqual('title_en', item.test.__class__.objects.only('title')[0].title)
        with override('de'):
            item = models.ForeignKeyModel.objects.select_related("test").defer("test__text")[0]
            self.assertDeferredClass(item.test)
            self.assertEqual('title_de', item.test.title)
            self.assertEqual('title_de', item.test.__class__.objects.only('title')[0].title)

    def test_deferred_spanning(self):
        test = models.TestModel.objects.create(title_de='title_de', title_en='title_en')
        with auto_populate('all'):
            models.ForeignKeyModel.objects.create(test=test)

        item1 = models.ForeignKeyModel.objects.select_related("test").defer("test__text")[0].test
        item2 = models.TestModel.objects.defer("text")[0]
        self.assertIs(item1.__class__, item2.__class__)
        # DeferredAttribute descriptors are present
        self.assertIn('text_en', dir(item1.__class__))
        self.assertIn('text_de', dir(item1.__class__))

    def test_deferred_rule2(self):
        models.TestModel.objects.create(title_de='title_de', title_en='title_en')
        o = models.TestModel.objects.only('title')[0]
        self.assertEqual(o.title, "title_en")
        o.title = "bla"
        self.assertEqual(o.title, "bla")

    @skipUnless(django.VERSION[0] == 1, 'Applicable only to django 1.x')
    def test_select_related_django_1(self):
        test = models.TestModel.objects.create(title_de='title_de', title_en='title_en')
        with auto_populate('all'):
            models.ForeignKeyModel.objects.create(untrans=test)

        fk_qs = models.ForeignKeyModel.objects.all()
        self.assertNotIn('_untrans_cache', fk_qs[0].__dict__)
        self.assertIn('_untrans_cache', fk_qs.select_related('untrans')[0].__dict__)
        self.assertNotIn(
            '_untrans_cache',
            fk_qs.select_related('untrans').select_related(None)[0].__dict__
        )
        # untrans is nullable so not included when select_related=True
        self.assertNotIn('_untrans_cache', fk_qs.select_related()[0].__dict__)

    @skipUnless(django.VERSION[0] >= 2, 'Applicable only to django > 2.x')
    def test_select_related_django_2(self):
        test = models.TestModel.objects.create(title_de='title_de', title_en='title_en')
        with auto_populate('all'):
            models.ForeignKeyModel.objects.create(untrans=test)

        fk_qs = models.ForeignKeyModel.objects.all()
        self.assertNotIn('untrans', fk_qs[0]._state.fields_cache)
        self.assertIn('untrans', fk_qs.select_related('untrans')[0]._state.fields_cache)
        self.assertNotIn(
            'untrans',
            fk_qs.select_related('untrans').select_related(None)[0]._state.fields_cache
        )
        # untrans is nullable so not included when select_related=True
        self.assertNotIn('untrans', fk_qs.select_related()[0]._state.fields_cache)

    def test_translation_fields_appending(self):
        from modeltranslation.manager import append_lookup_keys, append_lookup_key
        self.assertEqual(set(['untrans']), append_lookup_key(models.ForeignKeyModel, 'untrans'))
        self.assertEqual(set(['title', 'title_en', 'title_de']),
                         append_lookup_key(models.ForeignKeyModel, 'title'))
        self.assertEqual(set(['test', 'test_en', 'test_de']),
                         append_lookup_key(models.ForeignKeyModel, 'test'))
        self.assertEqual(set(['title__eq', 'title_en__eq', 'title_de__eq']),
                         append_lookup_key(models.ForeignKeyModel, 'title__eq'))
        self.assertEqual(set(['test__smt', 'test_en__smt', 'test_de__smt']),
                         append_lookup_key(models.ForeignKeyModel, 'test__smt'))
        big_set = set(['test__url', 'test__url_en', 'test__url_de',
                       'test_en__url', 'test_en__url_en', 'test_en__url_de',
                       'test_de__url', 'test_de__url_en', 'test_de__url_de'])
        self.assertEqual(big_set, append_lookup_key(models.ForeignKeyModel, 'test__url'))
        self.assertEqual(set(['untrans__url', 'untrans__url_en', 'untrans__url_de']),
                         append_lookup_key(models.ForeignKeyModel, 'untrans__url'))

        self.assertEqual(big_set.union(['title', 'title_en', 'title_de']),
                         append_lookup_keys(models.ForeignKeyModel, ['test__url', 'title']))

    def test_constructor_inheritance(self):
        inst = models.AbstractModelB()
        # Check if fields assigned in constructor hasn't been ignored.
        self.assertEqual(inst.titlea, 'title_a')
        self.assertEqual(inst.titleb, 'title_b')

    def test_distinct(self):
        """Check that field names are rewritten in distinct keys."""
        manager = models.ManagerTestModel.objects
        manager.create(
            title_en='title_1_en', title_de='title_1_de',
            description_en='desc_1_en', description_de='desc_1_de')
        manager.create(
            title_en='title_1_en', title_de='title_1_de',
            description_en='desc_2_en', description_de='desc_2_de')
        manager.create(
            title_en='title_2_en', title_de='title_2_de',
            description_en='desc_1_en', description_de='desc_1_de')
        manager.create(
            title_en='title_2_en', title_de='title_2_de',
            description_en='desc_2_en', description_de='desc_2_de')

        # Without field arguments to distinct() all fields are used to determine
        # distinctness, therefore when only looking at a subset of fields in the
        # queryset it can appear that there are duplicates (the titles in this case)
        titles_for_en = tuple(m.title for m in manager.order_by('title').distinct())
        with override('de'):
            titles_for_de = tuple(m.title for m in manager.order_by('title').distinct())

        self.assertEqual(titles_for_en, ('title_1_en', 'title_1_en', 'title_2_en', 'title_2_en'))
        self.assertEqual(titles_for_de, ('title_1_de', 'title_1_de', 'title_2_de', 'title_2_de'))

        # On PostgreSQL only, distinct() can have field arguments (*fields) to specify which fields
        # the distinct applies to (this generates a DISTINCT ON (*fields) sql expression).
        # NB: DISTINCT ON expressions must be accompanied by an order_by() that starts with the
        # same fields in the same order
        if django_settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
            titles_for_en = tuple(
                (m.title, m.description) for m in manager.order_by(
                    'title', 'description').distinct('title'))
            with override('de'):
                titles_for_de = tuple(
                    (m.title, m.description) for m in manager.order_by(
                        'title', 'description').distinct('title'))

            self.assertEqual(
                titles_for_en, (('title_1_en', 'desc_1_en'), ('title_2_en', 'desc_1_en')))
            self.assertEqual(
                titles_for_de, (('title_1_de', 'desc_1_de'), ('title_2_de', 'desc_1_de')))


class TranslationModelFormTest(ModeltranslationTestBase):
    def test_fields(self):
        class TestModelForm(TranslationModelForm):
            class Meta:
                model = models.TestModel
                fields = '__all__'

        form = TestModelForm()
        self.assertEqual(list(form.base_fields),
                         ['title', 'title_de', 'title_en', 'text', 'text_de', 'text_en',
                          'url', 'url_de', 'url_en', 'email', 'email_de', 'email_en'])
        self.assertEqual(list(form.fields), ['title', 'text', 'url', 'email'])

    def test_updating_with_empty_value(self):
        """
        Can we update the current language translation with an empty value, when
        the original field is excluded from the form?
        """
        class Form(forms.ModelForm):
            class Meta:
                model = models.TestModel
                exclude = ('text',)

        instance = models.TestModel.objects.create(text_de='something')
        form = Form({'text_de': '', 'title': 'a', 'email_de': '', 'email_en': ''},
                    instance=instance)
        instance = form.save()
        self.assertEqual('de', get_language())
        self.assertEqual('', instance.text_de)


class ProxyModelTest(ModeltranslationTestBase):
    def test_equality(self):
        n = models.TestModel.objects.create(title='Title')
        m = models.ProxyTestModel.objects.get(title='Title')
        self.assertEqual(n.title, m.title)
        self.assertEqual(n.title_de, m.title_de)
        self.assertEqual(n.title_en, m.title_en)


class TestRequired(ModeltranslationTestBase):
    def assertRequired(self, field_name):
        self.assertFalse(self.opts.get_field(field_name).blank)

    def assertNotRequired(self, field_name):
        self.assertTrue(self.opts.get_field(field_name).blank)

    def test_required(self):
        self.opts = models.RequiredModel._meta

        # All non required
        self.assertNotRequired('non_req')
        self.assertNotRequired('non_req_en')
        self.assertNotRequired('non_req_de')

        # Original required, but translated fields not - default behaviour
        self.assertRequired('req')
        self.assertNotRequired('req_en')
        self.assertNotRequired('req_de')

        # Set all translated field required
        self.assertRequired('req_reg')
        self.assertRequired('req_reg_en')
        self.assertRequired('req_reg_de')

        # Set some translated field required
        self.assertRequired('req_en_reg')
        self.assertRequired('req_en_reg_en')
        self.assertNotRequired('req_en_reg_de')

        # Test validation
        inst = models.RequiredModel()
        inst.req = 'abc'
        inst.req_reg = 'def'
        try:
            inst.full_clean()
        except ValidationError as e:
            error_fields = set(e.message_dict.keys())
            self.assertEqual(set(('req_reg_en', 'req_en_reg', 'req_en_reg_en')), error_fields)
        else:
            self.fail('ValidationError not raised!')


class M2MTest(ModeltranslationTestBase):
    def test_m2m(self):
        # Create 1 instance of Y, linked to 2 instance of X, with different
        # English and German names.
        x1 = models.ModelX.objects.create(name_en="foo", name_de="bar")
        x2 = models.ModelX.objects.create(name_en="bar", name_de="baz")
        y = models.ModelY.objects.create(title='y1')
        models.ModelXY.objects.create(model_x=x1, model_y=y)
        models.ModelXY.objects.create(model_x=x2, model_y=y)

        with override("en"):
            # There's 1 X named "foo" and it's x1
            y_foo = models.ModelY.objects.filter(xs__name="foo")
            self.assertEqual(1, y_foo.count())

            # There's 1 X named "bar" and it's x2 (in English)
            y_bar = models.ModelY.objects.filter(xs__name="bar")
            self.assertEqual(1, y_bar.count())

            # But in English, there's no X named "baz"
            y_baz = models.ModelY.objects.filter(xs__name="baz")
            self.assertEqual(0, y_baz.count())

            # Again: 1 X named "bar" (but through the M2M field)
            x_bar = y.xs.filter(name="bar")
            self.assertIn(x2, x_bar)


class InheritedPermissionTestCase(ModeltranslationTestBase):

    @skipUnless(MIGRATIONS, 'migrations/auth not available')
    def test_managers_failure(self):
        """This fails with 0.13b."""
        from modeltranslation.manager import MultilingualManager
        from django.contrib.auth.models import Permission, User
        from .models import InheritedPermission
        self.assertFalse(
            isinstance(Permission.objects, MultilingualManager),
            "Permission is using MultilingualManager")
        self.assertTrue(
            isinstance(InheritedPermission.objects, MultilingualManager),
            "InheritedPermission is not using MultilingualManager")

        # This happens at initialization time, depending on the models
        # initialized.
        Permission._meta._expire_cache()

        self.assertFalse(
            isinstance(Permission.objects, MultilingualManager),
            "Permission is using MultilingualManager")
        user = User.objects.create(username='123', is_active=True)
        user.has_perm('test_perm')
