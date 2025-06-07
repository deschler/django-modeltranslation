# pyright: reportGeneralTypeIssues=warning, reportOptionalMemberAccess=warning, reportOptionalOperand=warning
import datetime
import importlib
import os
import shutil
import sys
from decimal import Decimal

import pytest
from django import forms
from django.apps import apps as django_apps
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.db.models import CharField, Count, F, Q, Value
from django.db.models.functions import Cast, Concat
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils.translation import get_language, override, trans_real
from parameterized import parameterized  # type: ignore[import-untyped]

from modeltranslation import translator
from modeltranslation import settings as mt_settings
from modeltranslation.forms import TranslationModelForm
from modeltranslation.manager import MultilingualManager
from modeltranslation.models import autodiscover
from modeltranslation.tests import models, translation
from modeltranslation.utils import (
    auto_populate,
    build_lang,
    build_localized_fieldname,
    fallbacks,
)

# How many models are registered for tests.
TEST_MODELS = 41


class reload_override_settings(override_settings):
    """Context manager that not only override settings, but also reload modeltranslation conf."""

    def __enter__(self):
        super().__enter__()
        importlib.reload(mt_settings)

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        importlib.reload(mt_settings)


# In this test suite fallback language is turned off. This context manager temporarily turns it on.
def default_fallback():
    return reload_override_settings(
        MODELTRANSLATION_FALLBACK_LANGUAGES=(mt_settings.DEFAULT_LANGUAGE,)
    )


def get_field_names(model):
    names = set()
    fields = model._meta.get_fields()
    for field in fields:
        if field.is_relation and field.many_to_one and field.related_model is None:
            continue
        if field.model != model and field.model._meta.concrete_model == model._meta.concrete_model:
            continue

        names.add(field.name)
        if hasattr(field, "attname"):
            names.add(field.attname)
    return names


def assert_db_record(instance, **expected_fields):
    """
    Compares field values stored in the db.
    """
    actual = (
        type(instance)
        .objects.rewrite(False)
        .filter(pk=instance.pk)
        .values(*expected_fields.keys())
        .first()
    )
    assert actual == expected_fields


class ModeltranslationTransactionTestBase(TransactionTestCase):
    cache = django_apps

    @classmethod
    def setUpClass(cls):
        """Save registry (and restore it after tests)."""
        super().setUpClass()
        from copy import copy

        from modeltranslation.translator import translator

        cls.registry_cpy = copy(translator._registry)

    @classmethod
    def tearDownClass(cls):
        from modeltranslation.translator import translator

        translator._registry = cls.registry_cpy
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._old_language = get_language()
        trans_real.activate("de")

    def tearDown(self):
        super().tearDown()
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
        super()._pre_setup()
        # Add test_app to INSTALLED_APPS
        new_installed_apps = django_settings.INSTALLED_APPS + ("modeltranslation.tests.test_app",)
        self.__override = override_settings(INSTALLED_APPS=new_installed_apps)
        self.__override.enable()

    def _post_teardown(self):
        self.__override.disable()
        importlib.reload(mt_settings)  # restore mt_settings.FALLBACK_LANGUAGES
        super()._post_teardown()

    def tearDown(self):
        # Rollback model classes
        del self.cache.all_models["test_app"]
        from .test_app import models

        importlib.reload(models)
        # Delete translation modules from import cache
        sys.modules.pop("modeltranslation.tests.test_app.translation", None)
        sys.modules.pop("modeltranslation.tests.project_translation", None)
        super().tearDown()

    def check_news(self):
        from .test_app.models import News

        fields = dir(News())
        assert "title" in fields
        assert "title_en" in fields
        assert "title_de" in fields
        assert "visits" in fields
        assert "visits_en" not in fields
        assert "visits_de" not in fields

    def check_other(self, present=True):
        from .test_app.models import Other

        fields = dir(Other())
        assert "name" in fields
        if present:
            assert "name_en" in fields
            assert "name_de" in fields
        else:
            assert "name_en" not in fields
            assert "name_de" not in fields

    def test_simple(self):
        """Check if translation is imported for installed apps."""
        autodiscover()
        self.check_news()
        self.check_other(present=False)

    @reload_override_settings(
        MODELTRANSLATION_TRANSLATION_FILES=("modeltranslation.tests.project_translation",)
    )
    def test_global(self):
        """Check if translation is imported for global translation file."""
        autodiscover()
        self.check_news()
        self.check_other()

    @reload_override_settings(
        MODELTRANSLATION_TRANSLATION_FILES=("modeltranslation.tests.test_app.translation",)
    )
    def test_duplication(self):
        """Check if there is no problem with duplicated filenames."""
        autodiscover()
        self.check_news()


class ModeltranslationTest(ModeltranslationTestBase):
    """Basic tests for the modeltranslation application."""

    def test_registration(self):
        langs = tuple(val for val, label in django_settings.LANGUAGES)
        assert langs == tuple(mt_settings.AVAILABLE_LANGUAGES)
        assert 2 == len(langs)
        assert "de" in langs
        assert "en" in langs
        assert translator.translator

        # Check that all models are registered for translation
        assert len(translator.translator.get_registered_models()) == TEST_MODELS

        # Try to unregister a model that is not registered
        with pytest.raises(translator.NotRegistered):
            translator.translator.unregister(models.BasePage)

        # Try to get options for a model that is not registered
        with pytest.raises(translator.NotRegistered):
            translator.translator.get_options_for_model(
                models.ThirdPartyModel,
            )

        # Ensure that a base can't be registered after a subclass.
        with pytest.raises(translator.DescendantRegistered):
            translator.translator.register(models.BasePage)

        # Or unregistered before it.
        with pytest.raises(translator.DescendantRegistered):
            translator.translator.unregister(models.Slugged)

    def test_registration_field_conflicts(self):
        before = len(translator.translator.get_registered_models())

        # Exception should be raised when conflicting field name detected
        with pytest.raises(ValueError):
            translator.translator.register(models.ConflictModel, fields=("title",))
        with pytest.raises(ValueError):
            translator.translator.register(
                models.AbstractConflictModelB,
                fields=("title",),
            )
        with pytest.raises(ValueError):
            translator.translator.register(
                models.MultitableConflictModelB,
                fields=("title",),
            )

        # Model should not be registered
        assert len(translator.translator.get_registered_models()) == before

    def test_fields(self):
        field_names = dir(models.TestModel())
        assert "id" in field_names
        assert "title" in field_names
        assert "title_de" in field_names
        assert "title_en" in field_names
        assert "text" in field_names
        assert "text_de" in field_names
        assert "text_en" in field_names
        assert "url" in field_names
        assert "url_de" in field_names
        assert "url_en" in field_names
        assert "email" in field_names
        assert "email_de" in field_names
        assert "email_en" in field_names

    def test_verbose_name(self):
        verbose_name = models.TestModel._meta.get_field("title_de").verbose_name
        assert verbose_name == "title [de]"

    def test_custom_verbose_name(self):
        def get_verbose_name(verbose_name, language):
            return f"({language}) {verbose_name}"

        with reload_override_settings(
            MODELTRANSLATION_BUILD_LOCALIZED_VERBOSE_NAME=get_verbose_name
        ):
            verbose_name = models.TestModel._meta.get_field("title_de").verbose_name
            assert verbose_name == "(de) title"

    def test_descriptor_introspection(self):
        # See Django #8248
        assert isinstance(models.TestModel.title.__doc__, str), (
            "Descriptor accessed on class should return itself."
        )

    def test_fields_hashes(self):
        opts = models.TestModel._meta
        orig = opts.get_field("title")
        en = opts.get_field("title_en")
        de = opts.get_field("title_de")
        # Translation field retain creation_counters
        assert orig.creation_counter == en.creation_counter
        assert orig.creation_counter == de.creation_counter
        # But they compare unequal
        assert orig != en
        assert orig != de
        assert en != de
        # Their hashes too
        assert hash(orig) != hash(en)
        assert hash(orig) != hash(de)
        assert hash(en) != hash(de)
        assert 3 == len({orig, en, de})
        # TranslationFields can compare equal if they have the same language
        de.language = "en"
        assert orig != de
        assert en == de
        assert hash(en) == hash(de)
        assert 2 == len({orig, en, de})
        de.language = "de"

    def test_set_translation(self):
        """This test briefly shows main modeltranslation features."""
        assert get_language() == "de"
        title_de = "title de"
        title_en = "title en"

        # The original field "title" passed in the constructor is
        # populated for the current language field: "title_de".
        inst2 = models.TestModel(title=title_de)
        assert inst2.title == title_de
        assert inst2.title_en is None
        assert inst2.title_de == title_de

        # So creating object is language-aware
        with override("en"):
            inst2 = models.TestModel(title=title_en)
            assert inst2.title == title_en
            assert inst2.title_en == title_en
            assert inst2.title_de is None

        # Value from original field is presented in current language:
        inst2 = models.TestModel(title_de=title_de, title_en=title_en)
        assert inst2.title == title_de
        with override("en"):
            assert inst2.title == title_en

        # Changes made via original field affect current language field:
        inst2.title = "foo"
        assert inst2.title == "foo"
        assert inst2.title_en == title_en
        assert inst2.title_de == "foo"
        with override("en"):
            inst2.title = "bar"
            assert inst2.title == "bar"
            assert inst2.title_en == "bar"
            assert inst2.title_de == "foo"
        assert inst2.title == "foo"

        # When conflict, language field wins with original field
        inst2 = models.TestModel(title="foo", title_de=title_de, title_en=title_en)
        assert inst2.title == title_de
        assert inst2.title_en == title_en
        assert inst2.title_de == title_de

        # Creating model and assigning only one language
        inst1 = models.TestModel(title_en=title_en)
        # Please note: '' and not None, because descriptor falls back to field default value
        assert inst1.title == ""
        assert inst1.title_en == title_en
        assert inst1.title_de is None
        # Assign current language value - de
        inst1.title = title_de
        assert inst1.title == title_de
        assert inst1.title_en == title_en
        assert inst1.title_de == title_de
        inst1.save()

        # Check that the translation fields are correctly saved and provide the
        # correct value when retrieving them again.
        n = models.TestModel.objects.get(title=title_de)
        assert n.title == title_de
        assert n.title_en == title_en
        assert n.title_de == title_de
        assert_db_record(n, title=title_de, title_de=title_de, title_en=title_en)

        # Queries are also language-aware:
        assert 1 == models.TestModel.objects.filter(title=title_de).count()
        with override("en"):
            assert 0 == models.TestModel.objects.filter(title=title_de).count()

    def test_fallback_language(self):
        # Present what happens if current language field is empty
        assert get_language() == "de"
        title_de = "title de"

        # Create model with value in de only...
        inst2 = models.TestModel(title=title_de)
        assert inst2.title == title_de
        assert inst2.title_en is None
        assert inst2.title_de == title_de

        # In this test environment, fallback language is not set. So return value for en
        # will be field's default: ''
        with override("en"):
            assert inst2.title == ""
            assert inst2.title_en is None  # Language field access returns real value

        # However, by default FALLBACK_LANGUAGES is set to DEFAULT_LANGUAGE
        with default_fallback():
            # No change here...
            assert inst2.title == title_de

            # ... but for empty en fall back to de
            with override("en"):
                assert inst2.title == title_de
                assert inst2.title_en is None  # Still real value

    def test_fallback_values_1(self):
        """
        If ``fallback_values`` is set to string, all untranslated fields would
        return this string.
        """
        title1_de = "title de"
        n = models.FallbackModel(title=title1_de)
        n.save()
        n = models.FallbackModel.objects.get(title=title1_de)
        assert n.title == title1_de
        trans_real.activate("en")
        assert n.title == "fallback"

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
        assert n.title == ""  # Falling back to default field value
        assert n.text == translation.FallbackModel2TranslationOptions.fallback_values["text"]

    def _compare_instances(self, x, y, field):
        assert getattr(x, field) == getattr(y, field), "Constructor diff on field %s." % field

    def _test_constructor(self, keywords):
        n = models.TestModel(**keywords)
        m = models.TestModel.objects.create(**keywords)
        opts = translator.translator.get_options_for_model(models.TestModel)
        for base_field, trans_fields in opts.all_fields.items():
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
            title="title",
            # both languages + original
            email="q@q.qq",
            email_de="d@d.dd",
            email_en="e@e.ee",
            # both languages without original
            text_en="text en",
            text_de="text de",
        )
        self._test_constructor(keywords)

        keywords = dict(
            # only current language
            title_de="title",
            # only not current language
            url_en="http://www.google.com",
            # original + current
            text="text def",
            text_de="text de",
            # original + not current
            email="q@q.qq",
            email_en="e@e.ee",
        )
        self._test_constructor(keywords)

    @parameterized.expand(
        [
            ({"title": "DE"}, ["title"], {"title": "DE", "title_de": "DE", "title_en": None}),
            ({"title_de": "DE"}, ["title"], {"title": "DE", "title_de": "DE", "title_en": None}),
            ({"title": "DE"}, ["title_de"], {"title": "old", "title_de": "DE", "title_en": None}),
            (
                {"title_de": "DE"},
                ["title_de"],
                {"title": "old", "title_de": "DE", "title_en": None},
            ),
            (
                {"title": "DE", "title_en": "EN"},
                ["title", "title_en"],
                {"title": "DE", "title_de": "DE", "title_en": "EN"},
            ),
            (
                {"title_de": "DE", "title_en": "EN"},
                ["title_de", "title_en"],
                {"title": "old", "title_de": "DE", "title_en": "EN"},
            ),
            (
                {"title_de": "DE", "title_en": "EN"},
                ["title", "title_de", "title_en"],
                {"title": "DE", "title_de": "DE", "title_en": "EN"},
            ),
        ]
    )
    def test_save_original_translation_field(self, field_values, update_fields, expected_db_values):
        obj = models.TestModel.objects.create(title="old")

        for field, value in field_values.items():
            setattr(obj, field, value)

        obj.save(update_fields=update_fields)
        assert_db_record(obj, **expected_db_values)

    @parameterized.expand(
        [
            ({"title": "EN"}, ["title"], {"title": "EN", "title_de": None, "title_en": "EN"}),
            ({"title_en": "EN"}, ["title"], {"title": "EN", "title_de": None, "title_en": "EN"}),
            ({"title": "EN"}, ["title_en"], {"title": "old", "title_de": None, "title_en": "EN"}),
            (
                {"title_en": "EN"},
                ["title_en"],
                {"title": "old", "title_de": None, "title_en": "EN"},
            ),
            (
                {"title": "EN", "title_de": "DE"},
                ["title", "title_de"],
                {"title": "EN", "title_de": "DE", "title_en": "EN"},
            ),
            (
                {"title_de": "DE", "title_en": "EN"},
                ["title_de", "title_en"],
                {"title": "old", "title_de": "DE", "title_en": "EN"},
            ),
            (
                {"title_de": "DE", "title_en": "EN"},
                ["title", "title_de", "title_en"],
                {"title": "EN", "title_de": "DE", "title_en": "EN"},
            ),
        ]
    )
    def test_save_active_translation_field(self, field_values, update_fields, expected_db_values):
        with override("en"):
            obj = models.TestModel.objects.create(title="old")

            for field, value in field_values.items():
                setattr(obj, field, value)

            obj.save(update_fields=update_fields)
            assert_db_record(obj, **expected_db_values)

    def test_save_non_original_translation_field(self):
        obj = models.TestModel.objects.create(title="old")

        obj.title_en = "en value"
        obj.save(update_fields=["title"])
        assert_db_record(obj, title="old", title_de="old", title_en=None)

        obj.save(update_fields=["title_en"])
        assert_db_record(obj, title="old", title_de="old", title_en="en value")

    def test_update_or_create_existing(self):
        """
        Test that update_or_create works as expected
        """
        obj = models.TestModel.objects.create(title_de="old de", title_en="old en")

        instance, created = models.TestModel.objects.update_or_create(
            pk=obj.pk, defaults={"title": "NEW DE TITLE"}
        )

        assert created is False
        assert instance.title == "NEW DE TITLE"
        assert instance.title_en == "old en"
        assert instance.title_de == "NEW DE TITLE"
        assert_db_record(
            instance,
            title="NEW DE TITLE",
            title_en="old en",
            title_de="NEW DE TITLE",
        )

        instance, created = models.TestModel.objects.update_or_create(
            pk=obj.pk, defaults={"title_de": "NEW DE TITLE 2"}
        )

        assert created is False
        assert instance.title == "NEW DE TITLE 2"
        assert instance.title_en == "old en"
        assert instance.title_de == "NEW DE TITLE 2"
        assert_db_record(
            instance,
            # title='NEW DE TITLE',  # TODO: django < 4.2 doesn't pass `"title"` into `.save(update_fields)`
            title_en="old en",
            title_de="NEW DE TITLE 2",
        )

        with override("en"):
            instance, created = models.TestModel.objects.update_or_create(
                pk=obj.pk, defaults={"title": "NEW EN TITLE"}
            )

            assert created is False
            assert instance.title == "NEW EN TITLE"
            assert instance.title_en == "NEW EN TITLE"
            assert instance.title_de == "NEW DE TITLE 2"
            assert_db_record(
                instance,
                title="NEW EN TITLE",
                title_en="NEW EN TITLE",
                title_de="NEW DE TITLE 2",
            )

    def test_update_or_create_new(self):
        instance, created = models.TestModel.objects.update_or_create(
            pk=1,
            defaults={"title_de": "old de", "title_en": "old en"},
        )

        assert created is True
        assert instance.title == "old de"
        assert instance.title_en == "old en"
        assert instance.title_de == "old de"
        assert_db_record(
            instance,
            title="old de",
            title_en="old en",
            title_de="old de",
        )

    def test_callable_field_default_uses_field_language(self):
        # the test uses translations from django.contrib.auth django.po file by
        # specifying a model default with one of the translatable literals from that
        # app

        # unsaved instance must follow django's behaviour for callable default
        raw_instance = models.TestModel()

        assert raw_instance.dynamic_default == "Passwort"
        assert raw_instance.dynamic_default_en == "password"
        assert raw_instance.dynamic_default_de == "Passwort"

        # saved instance must have same behaviour as unsaved instance
        instance = models.TestModel.objects.create()

        assert instance.dynamic_default == "Passwort"
        assert instance.dynamic_default_en == "password"
        assert instance.dynamic_default_de == "Passwort"
        assert_db_record(
            instance,
            dynamic_default="Passwort",
            dynamic_default_en="password",
            dynamic_default_de="Passwort",
        )


class ModeltranslationTransactionTest(ModeltranslationTransactionTestBase):
    def test_unique_nullable_field(self):
        from django.db import transaction

        models.UniqueNullableModel.objects.create()
        models.UniqueNullableModel.objects.create()
        models.UniqueNullableModel.objects.create(title=None)
        models.UniqueNullableModel.objects.create(title=None)

        models.UniqueNullableModel.objects.create(title="")
        with pytest.raises(IntegrityError):
            models.UniqueNullableModel.objects.create(title="")
        transaction.rollback()  # Postgres
        models.UniqueNullableModel.objects.create(title="foo")
        with pytest.raises(IntegrityError):
            models.UniqueNullableModel.objects.create(title="foo")
        transaction.rollback()  # Postgres


class FallbackTests(ModeltranslationTestBase):
    test_fallback = {"default": ("de",), "de": ("en",)}

    def test_settings(self):
        # Initial
        assert mt_settings.FALLBACK_LANGUAGES == {"default": ()}
        # Tuple/list
        with reload_override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=("de",)):
            assert mt_settings.FALLBACK_LANGUAGES == {"default": ("de",)}
        # Whole dict
        with reload_override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=self.test_fallback):
            assert mt_settings.FALLBACK_LANGUAGES == self.test_fallback
        # Improper language raises error
        config = {"default": (), "fr": ("en",)}
        with override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=config):
            with pytest.raises(ImproperlyConfigured):
                importlib.reload(mt_settings)
        importlib.reload(mt_settings)

    def test_resolution_order(self):
        from modeltranslation.utils import resolution_order

        with reload_override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=self.test_fallback):
            assert ("en", "de") == resolution_order("en")
            assert ("de", "en") == resolution_order("de")
            # Overriding
            config = {"default": ()}
            assert ("en",) == resolution_order("en", config)
            assert ("de", "en") == resolution_order("de", config)
            # Uniqueness
            config = {"de": ("en", "de")}
            assert ("en", "de") == resolution_order("en", config)
            assert ("de", "en") == resolution_order("de", config)

            # Default fallbacks are always used at the end
            # That's it: fallbacks specified for a language don't replace defaults,
            # but just are prepended
            config = {"default": ("en", "de"), "de": ()}
            assert ("en", "de") == resolution_order("en", config)
            assert ("de", "en") == resolution_order("de", config)
            # What one may have expected
            assert ("de",) != resolution_order("de", config)

            # To completely override settings, one should override all keys
            config = {"default": (), "de": ()}
            assert ("en",) == resolution_order("en", config)
            assert ("de",) == resolution_order("de", config)

    def test_fallback_languages(self):
        with reload_override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=self.test_fallback):
            title_de = "title de"
            title_en = "title en"
            n = models.TestModel(title=title_de)
            assert n.title_de == title_de
            assert n.title_en is None
            assert n.title == title_de
            trans_real.activate("en")
            assert n.title == title_de  # since default fallback is de

            n = models.TestModel(title=title_en)
            assert n.title_de is None
            assert n.title_en == title_en
            assert n.title == title_en
            trans_real.activate("de")
            assert n.title == title_en  # since fallback for de is en

            n.title_en = None
            assert n.title == ""  # if all fallbacks fail, return field.get_default()

    def test_fallbacks_toggle(self):
        with reload_override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=self.test_fallback):
            m = models.TestModel(title="foo")
            with fallbacks(True):
                assert m.title_de == "foo"
                assert m.title_en is None
                assert m.title == "foo"
                with override("en"):
                    assert m.title == "foo"
            with fallbacks(False):
                assert m.title_de == "foo"
                assert m.title_en is None
                assert m.title == "foo"
                with override("en"):
                    assert m.title == ""  # '' is the default

    def test_fallback_undefined(self):
        """
        Checks if a sensible value is considered undefined and triggers
        fallbacks. Tests if the value can be overridden as documented.
        """
        with reload_override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=self.test_fallback):
            # Non-nullable CharField falls back on empty strings.
            m = models.FallbackModel(title_en="value", title_de="")
            with override("en"):
                assert m.title == "value"
            with override("de"):
                assert m.title == "value"

            # Nullable CharField does not fall back on empty strings.
            m = models.FallbackModel(description_en="value", description_de="")
            with override("en"):
                assert m.description == "value"
            with override("de"):
                assert m.description == ""

            # Nullable CharField does fall back on None.
            m = models.FallbackModel(description_en="value", description_de=None)
            with override("en"):
                assert m.description == "value"
            with override("de"):
                assert m.description == "value"

            # The undefined value may be overridden.
            m = models.FallbackModel2(title_en="value", title_de="")
            with override("en"):
                assert m.title == "value"
            with override("de"):
                assert m.title == ""
            m = models.FallbackModel2(title_en="value", title_de="no title")
            with override("en"):
                assert m.title == "value"
            with override("de"):
                assert m.title == "value"


class FileFieldsTest(ModeltranslationTestBase):
    def tearDown(self):
        if default_storage.exists("modeltranslation_tests"):
            # With FileSystemStorage uploading files creates a new directory,
            # that's not automatically removed upon their deletion.
            tests_dir = default_storage.path("modeltranslation_tests")
            if os.path.isdir(tests_dir):
                shutil.rmtree(tests_dir)
        super().tearDown()

    def test_translated_models(self):
        field_names = dir(models.FileFieldsModel())
        assert "id" in field_names
        assert "title" in field_names
        assert "title_de" in field_names
        assert "title_en" in field_names
        assert "file" in field_names
        assert "file_de" in field_names
        assert "file_en" in field_names
        assert "image" in field_names
        assert "image_de" in field_names
        assert "image_en" in field_names

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
        inst.title = "title_en"
        inst.file = "a_en"
        inst.file.save("b_en", ContentFile("file in english"))
        inst.image = self._file_factory("i_en.jpg", "image in english")  # Direct assign

        trans_real.activate("de")
        inst.title = "title_de"
        inst.file = "a_de"
        inst.file.save("b_de", ContentFile("file in german"))
        inst.image = self._file_factory("i_de.jpg", "image in german")

        inst.save()

        trans_real.activate("en")
        assert inst.title == "title_en"
        assert inst.file.name.count("b_en") > 0
        assert inst.file.read() == b"file in english"
        assert inst.image.name.count("i_en") > 0
        assert inst.image.read() == b"image in english"

        # Check if file was actually created in the global storage.
        assert default_storage.exists(inst.file.path)
        assert inst.file.size > 0
        assert default_storage.exists(inst.image.path)
        assert inst.image.size > 0

        trans_real.activate("de")
        assert inst.title == "title_de"
        assert inst.file.name.count("b_de") > 0
        assert inst.file.read() == b"file in german"
        assert inst.image.name.count("i_de") > 0
        assert inst.image.read() == b"image in german"

        inst.file_en.delete()
        inst.image_en.delete()
        inst.file_de.delete()
        inst.image_de.delete()

    def test_empty_field(self):
        from django.db.models.fields.files import FieldFile

        inst = models.FileFieldsModel()
        assert isinstance(inst.file, FieldFile)
        assert isinstance(inst.file2, FieldFile)
        inst.save()
        inst = models.FileFieldsModel.objects.all()[0]
        assert isinstance(inst.file, FieldFile)
        assert isinstance(inst.file2, FieldFile)

    def test_fallback(self):
        from django.db.models.fields.files import FieldFile

        with reload_override_settings(MODELTRANSLATION_FALLBACK_LANGUAGES=("en",)):
            assert get_language() == "de"
            inst = models.FileFieldsModel()
            inst.file_de = ""
            inst.file_en = "foo"
            inst.file2_de = ""
            inst.file2_en = "bar"
            assert isinstance(inst.file, FieldFile)
            assert isinstance(inst.file2, FieldFile)
            assert inst.file.name == "foo"
            assert inst.file2.name == "bar"
            inst.save()
            inst = models.FileFieldsModel.objects.all()[0]
            assert isinstance(inst.file, FieldFile)
            assert isinstance(inst.file2, FieldFile)
            assert inst.file.name == "foo"
            assert inst.file2.name == "bar"


class ForeignKeyFieldsTest(ModeltranslationTestBase):
    @classmethod
    def setUpClass(cls):
        # 'model' attribute cannot be assigned to class in its definition,
        # because ``models`` module will be reloaded and hence class would use old model classes.
        super().setUpClass()
        cls.model = models.ForeignKeyModel

    def test_translated_models(self):
        field_names = dir(self.model())
        assert "id" in field_names
        for f in ("test", "test_de", "test_en", "optional", "optional_en", "optional_de"):
            assert f in field_names
            assert "%s_id" % f in field_names

    def test_db_column_names(self):
        meta = self.model._meta

        # Make sure the correct database columns always get used:
        attname, col = meta.get_field("test").get_attname_column()
        assert attname == "test_id"
        assert attname == col

        attname, col = meta.get_field("test_en").get_attname_column()
        assert attname == "test_en_id"
        assert attname == col

        attname, col = meta.get_field("test_de").get_attname_column()
        assert attname == "test_de_id"
        assert attname == col

    def test_translated_models_instance(self):
        instance1 = models.TestModel(title_en="title1_en", title_de="title1_de")
        instance1.save()
        instance2 = models.TestModel(title_en="title2_en", title_de="title2_de")
        instance2.save()
        inst = self.model()

        trans_real.activate("de")
        inst.test = instance1
        inst.optional = None

        trans_real.activate("en")
        # Test assigning relation by ID:
        inst.optional_id = instance2.pk
        inst.save()

        trans_real.activate("de")
        assert inst.test_id == instance1.pk
        assert inst.test.title == "title1_de"
        assert inst.test_de_id == instance1.pk
        assert inst.test_de.title == "title1_de"
        assert inst.optional is None

        # Test fallbacks:
        trans_real.activate("en")
        with default_fallback():
            assert inst.test_id == instance1.pk
            assert inst.test.pk == instance1.pk
            assert inst.test.title == "title1_en"

        # Test English:
        assert inst.optional_id == instance2.pk
        assert inst.optional.title == "title2_en"
        assert inst.optional_en_id == instance2.pk
        assert inst.optional_en.title == "title2_en"

        # Test caching
        inst.test_en = instance2
        inst.save()
        trans_real.activate("de")
        assert inst.test == instance1
        trans_real.activate("en")
        assert inst.test == instance2

        # Check filtering in direct way + lookup spanning
        manager = self.model.objects
        trans_real.activate("de")
        assert manager.filter(test=instance1).count() == 1
        assert manager.filter(test_en=instance1).count() == 0
        assert manager.filter(test_de=instance1).count() == 1
        assert manager.filter(test=instance2).count() == 0
        assert manager.filter(test_en=instance2).count() == 1
        assert manager.filter(test_de=instance2).count() == 0
        assert manager.filter(test__title="title1_de").count() == 1
        assert manager.filter(test__title="title1_en").count() == 0
        assert manager.filter(test__title_en="title1_en").count() == 1
        trans_real.activate("en")
        assert manager.filter(test=instance1).count() == 0
        assert manager.filter(test_en=instance1).count() == 0
        assert manager.filter(test_de=instance1).count() == 1
        assert manager.filter(test=instance2).count() == 1
        assert manager.filter(test_en=instance2).count() == 1
        assert manager.filter(test_de=instance2).count() == 0
        assert manager.filter(test__title="title2_en").count() == 1
        assert manager.filter(test__title="title2_de").count() == 0
        assert manager.filter(test__title_de="title2_de").count() == 1

    def test_reverse_relations(self):
        instance = models.TestModel(title_en="title_en", title_de="title_de")
        instance.save()

        # Instantiate many 'ForeignKeyModel' instances:
        fk_inst_both = self.model(
            title_en="f_title_en", title_de="f_title_de", test_de=instance, test_en=instance
        )
        fk_inst_both.save()
        fk_inst_de = self.model(
            title_en="f_title_en", title_de="f_title_de", test_de_id=instance.pk
        )
        fk_inst_de.save()
        fk_inst_en = self.model(title_en="f_title_en", title_de="f_title_de", test_en=instance)
        fk_inst_en.save()

        fk_option_de = self.model.objects.create(optional_de=instance)
        fk_option_en = self.model.objects.create(optional_en=instance)

        # Check that the reverse accessors are created on the model:
        # Explicit related_name
        testmodel_fields = get_field_names(models.TestModel)
        testmodel_methods = set(dir(models.TestModel))

        assert {"test_fks", "test_fks_de", "test_fks_en"} <= testmodel_fields
        assert {"test_fks", "test_fks_de", "test_fks_en"} <= testmodel_methods
        # Implicit related_name: manager descriptor name != query field name
        assert {"foreignkeymodel", "foreignkeymodel_de", "foreignkeymodel_en"} <= testmodel_fields
        assert {
            "foreignkeymodel_set",
            "foreignkeymodel_set_de",
            "foreignkeymodel_set_en",
        } <= testmodel_methods

        # Check the German reverse accessor:
        assert fk_inst_both in instance.test_fks_de.all()
        assert fk_inst_de in instance.test_fks_de.all()
        assert fk_inst_en not in instance.test_fks_de.all()

        # Check the English reverse accessor:
        assert fk_inst_both in instance.test_fks_en.all()
        assert fk_inst_en in instance.test_fks_en.all()
        assert fk_inst_de not in instance.test_fks_en.all()

        # Check the default reverse accessor:
        trans_real.activate("de")
        assert fk_inst_de in instance.test_fks.all()
        assert fk_inst_en not in instance.test_fks.all()
        trans_real.activate("en")
        assert fk_inst_en in instance.test_fks.all()
        assert fk_inst_de not in instance.test_fks.all()

        # Check implicit related_name reverse accessor:
        assert fk_option_en in instance.foreignkeymodel_set.all()

        # Check filtering in reverse way + lookup spanning:

        manager = models.TestModel.objects
        trans_real.activate("de")
        assert manager.filter(test_fks=fk_inst_both).count() == 1
        assert manager.filter(test_fks=fk_inst_de).count() == 1
        assert manager.filter(test_fks__id=fk_inst_de.pk).count() == 1
        assert manager.filter(test_fks=fk_inst_en).count() == 0
        assert manager.filter(test_fks_en=fk_inst_en).count() == 1
        assert manager.filter(foreignkeymodel=fk_option_de).count() == 1
        assert manager.filter(foreignkeymodel=fk_option_en).count() == 0
        assert manager.filter(foreignkeymodel_en=fk_option_en).count() == 1
        assert manager.filter(test_fks__title="f_title_de").distinct().count() == 1
        assert manager.filter(test_fks__title="f_title_en").distinct().count() == 0
        assert manager.filter(test_fks__title_en="f_title_en").distinct().count() == 1
        trans_real.activate("en")
        assert manager.filter(test_fks=fk_inst_both).count() == 1
        assert manager.filter(test_fks=fk_inst_en).count() == 1
        assert manager.filter(test_fks__id=fk_inst_en.pk).count() == 1
        assert manager.filter(test_fks=fk_inst_de).count() == 0
        assert manager.filter(test_fks_de=fk_inst_de).count() == 1
        assert manager.filter(foreignkeymodel=fk_option_en).count() == 1
        assert manager.filter(foreignkeymodel=fk_option_de).count() == 0
        assert manager.filter(foreignkeymodel_de=fk_option_de).count() == 1
        assert manager.filter(test_fks__title="f_title_en").distinct().count() == 1
        assert manager.filter(test_fks__title="f_title_de").distinct().count() == 0
        assert manager.filter(test_fks__title_de="f_title_de").distinct().count() == 1

        # Check assignment
        trans_real.activate("de")
        instance2 = models.TestModel(title_en="title_en", title_de="title_de")
        instance2.save()
        instance2.test_fks.set((fk_inst_de, fk_inst_both))
        instance2.test_fks_en.set((fk_inst_en, fk_inst_both))

        assert fk_inst_both.test.pk == instance2.pk
        assert fk_inst_both.test_id == instance2.pk
        assert fk_inst_both.test_de == instance2
        assert set(instance2.test_fks_de.all()) == set(instance2.test_fks.all())
        assert fk_inst_both in instance2.test_fks.all()
        assert fk_inst_de in instance2.test_fks.all()
        assert fk_inst_en not in instance2.test_fks.all()
        trans_real.activate("en")
        assert set(instance2.test_fks_en.all()) == set(instance2.test_fks.all())
        assert fk_inst_both in instance2.test_fks.all()
        assert fk_inst_en in instance2.test_fks.all()
        assert fk_inst_de not in instance2.test_fks.all()

    def test_reverse_lookup_with_filtered_queryset_manager(self):
        """
        Make sure base_manager does not get same queryset filter as TestModel in reverse lookup
        https://docs.djangoproject.com/en/3.0/topics/db/managers/#base-managers
        """
        from modeltranslation.tests.models import FilteredManager

        instance = models.FilteredTestModel(title_en="title_en", title_de="title_de")
        instance.save()

        assert not models.FilteredTestModel.objects.all().exists()
        assert models.FilteredTestModel.objects.__class__ == FilteredManager
        assert models.FilteredTestModel._meta.base_manager.__class__ == MultilingualManager

        # # create objects with relations to instance
        fk_inst = models.ForeignKeyFilteredModel(
            test=instance, title_en="f_title_en", title_de="f_title_de"
        )
        fk_inst.save()
        fk_inst.refresh_from_db()  # force to reset cached values

        assert models.ForeignKeyFilteredModel.objects.__class__ == MultilingualManager
        assert models.ForeignKeyFilteredModel._meta.base_manager.__class__ == MultilingualManager
        assert fk_inst.test == instance

    def test_non_translated_relation(self):
        non_de = models.NonTranslated.objects.create(title="title_de")
        non_en = models.NonTranslated.objects.create(title="title_en")

        fk_inst_both = self.model.objects.create(
            title_en="f_title_en", title_de="f_title_de", non_de=non_de, non_en=non_en
        )
        fk_inst_de = self.model.objects.create(non_de=non_de)
        fk_inst_en = self.model.objects.create(non_en=non_en)

        # Forward relation + spanning
        manager = self.model.objects
        trans_real.activate("de")
        assert manager.filter(non=non_de).count() == 2
        assert manager.filter(non=non_en).count() == 0
        assert manager.filter(non_en=non_en).count() == 2
        assert manager.filter(non__title="title_de").count() == 2
        assert manager.filter(non__title="title_en").count() == 0
        assert manager.filter(non_en__title="title_en").count() == 2
        trans_real.activate("en")
        assert manager.filter(non=non_en).count() == 2
        assert manager.filter(non=non_de).count() == 0
        assert manager.filter(non_de=non_de).count() == 2
        assert manager.filter(non__title="title_en").count() == 2
        assert manager.filter(non__title="title_de").count() == 0
        assert manager.filter(non_de__title="title_de").count() == 2

        # Reverse relation + spanning
        manager = models.NonTranslated.objects
        trans_real.activate("de")
        assert manager.filter(test_fks=fk_inst_both).count() == 1
        assert manager.filter(test_fks=fk_inst_de).count() == 1
        assert manager.filter(test_fks=fk_inst_en).count() == 0
        assert manager.filter(test_fks_en=fk_inst_en).count() == 1
        assert manager.filter(test_fks__title="f_title_de").count() == 1
        assert manager.filter(test_fks__title="f_title_en").count() == 0
        assert manager.filter(test_fks__title_en="f_title_en").count() == 1
        trans_real.activate("en")
        assert manager.filter(test_fks=fk_inst_both).count() == 1
        assert manager.filter(test_fks=fk_inst_en).count() == 1
        assert manager.filter(test_fks=fk_inst_de).count() == 0
        assert manager.filter(test_fks_de=fk_inst_de).count() == 1
        assert manager.filter(test_fks__title="f_title_en").count() == 1
        assert manager.filter(test_fks__title="f_title_de").count() == 0
        assert manager.filter(test_fks__title_de="f_title_de").count() == 1

    def test_indonesian(self):
        field = models.ForeignKeyModel._meta.get_field("test")
        assert field.attname != build_localized_fieldname(field.name, "id")

    def test_build_lang(self):
        assert build_lang("en") == "en"
        assert build_lang("en_en") == "en_en"
        assert build_lang("en-en") == "en_en"
        assert build_lang("id") == "ind"


class ManyToManyFieldsTest(ModeltranslationTestBase):
    @classmethod
    def setUpClass(cls):
        # 'model' attribute cannot be assigned to class in its definition,
        # because ``models`` module will be reloaded and hence class would use old model classes.
        super().setUpClass()
        cls.model = models.ManyToManyFieldModel

    def test_translated_models(self):
        field_names = dir(self.model())
        assert "id" in field_names
        for f in ("test", "test_de", "test_en", "self_call_1", "self_call_1_en", "self_call_1_de"):
            assert f in field_names

    def test_db_column_names(self):
        meta = self.model._meta

        # Make sure the correct database columns always get used:
        field = meta.get_field("test")
        assert field.remote_field.through._meta.db_table == "tests_manytomanyfieldmodel_test"

        field = meta.get_field("test_en")
        assert field.remote_field.through._meta.db_table == "tests_manytomanyfieldmodel_test_en"

        field = meta.get_field("test_de")
        assert field.remote_field.through._meta.db_table == "tests_manytomanyfieldmodel_test_de"

        field = meta.get_field("self_call_1")
        assert field.remote_field.through._meta.db_table == "tests_manytomanyfieldmodel_self_call_1"

        field = meta.get_field("self_call_1_en")
        assert (
            field.remote_field.through._meta.db_table == "tests_manytomanyfieldmodel_self_call_1_en"
        )

        field = meta.get_field("self_call_1_de")
        assert (
            field.remote_field.through._meta.db_table == "tests_manytomanyfieldmodel_self_call_1_de"
        )

        field = meta.get_field("through_model")
        assert field.remote_field.through._meta.db_table == "tests_customthroughmodel"

        field = meta.get_field("through_model_en")
        assert field.remote_field.through._meta.db_table == "tests_customthroughmodel_en"

        field = meta.get_field("through_model_de")
        assert field.remote_field.through._meta.db_table == "tests_customthroughmodel_de"

    def test_translated_models_instance(self):
        models.TestModel.objects.bulk_create(
            models.TestModel(title_en="m2m_test_%s_en" % i, title_de="m2m_test_%s_de" % i)
            for i in range(10)
        )
        self.model.objects.bulk_create(
            self.model(title_en="m2m_test_%s_en" % i, title_de="m2m_test_%s_de" % i)
            for i in range(10)
        )
        models.NonTranslated.objects.bulk_create(
            models.NonTranslated(title="m2m_test_%s" % i) for i in range(10)
        )

        testmodel_qs = models.TestModel.objects.all()
        testmodel_qs_1 = testmodel_qs.filter(title_en__in=["m2m_test_%s_en" % i for i in range(4)])
        testmodel_qs_2 = testmodel_qs.filter(
            title_en__in=["m2m_test_%s_en" % i for i in range(4, 10)]
        )
        untranslated_qs = models.NonTranslated.objects.all()
        self_qs = self.model.objects.all()
        self_qs_1 = self_qs.filter(title_en__in=["m2m_test_%s_en" % i for i in range(6)])
        self_qs_2 = self_qs.filter(title_en__in=["m2m_test_%s_en" % i for i in range(6, 10)])

        inst = self.model()
        inst.save()

        trans_real.activate("de")
        inst.test.set(list(testmodel_qs_1.values_list("pk", flat=True)))
        assert inst.test.through.objects.all().count() == testmodel_qs_1.count()

        inst.through_model.set(testmodel_qs_2)
        assert inst.through_model.through.objects.all().count() == testmodel_qs_2.count()

        inst.self_call_2.set(self_qs_1)
        assert inst.self_call_2.all().count() == self_qs_1.count()

        trans_real.activate("en")
        inst.trans_through_model.through.objects.bulk_create(
            (
                inst.trans_through_model.through(
                    title_en="m2m_test_%s_en" % (i + 1),
                    title_de="m2m_test_%s_de" % (i + 1),
                    rel_1_id=int(inst.pk),
                    rel_2_id=tst_model.pk,
                )
                for i, tst_model in enumerate(testmodel_qs[:2])
            )
        )
        assert inst.trans_through_model.all().count() == 2

        inst.untrans.set(untranslated_qs)
        assert inst.untrans.through.objects.all().count() == untranslated_qs.count()

        inst.self_call_1.set(self_qs_2)
        assert (
            inst.self_call_1.filter(pk__in=self_qs_2.values_list("pk", flat=True)).count()
            == self_qs_2.count()
        )

        trans_real.activate("de")
        assert inst.test.through.objects.all().count() == testmodel_qs_1.count()
        assert inst.through_model.through.objects.all().count() == testmodel_qs_2.count()
        assert inst.untrans.through.objects.count() == 0
        assert inst.self_call_1.count() == 0

        assert inst.trans_through_model == getattr(inst, "trans_through_model_de")

        # Test prevent fallbacks:
        trans_real.activate("en")
        with default_fallback():
            assert inst.untrans.through.objects.all().count() == untranslated_qs.count()
            assert inst.trans_through_model == getattr(inst, "trans_through_model_en")

        # Test through properties and methods inheriance:
        trans_real.activate("de")
        through_inst = inst.through_model.through.objects.first()
        assert through_inst.test_property == "CustomThroughModel_de_%s" % inst.pk
        assert through_inst.test_method() == inst.pk + 1

        # Check filtering in direct way + lookup spanning
        manager = self.model.objects
        trans_real.activate("de")
        assert manager.filter(test__in=testmodel_qs_1).distinct().count() == 1
        assert manager.filter(test_en__in=testmodel_qs_1).distinct().count() == 0
        assert manager.filter(test_de__in=testmodel_qs_1).distinct().count() == 1

        assert (
            manager.filter(through_model__title__in=testmodel_qs_2.values_list("title", flat=True))
            .distinct()
            .count()
            == 1
        )
        assert (
            manager.filter(
                through_model_en__title__in=testmodel_qs_2.values_list("title", flat=True)
            ).count()
            == 0
        )
        assert (
            manager.filter(
                through_model_de__title__in=testmodel_qs_2.values_list("title", flat=True)
            )
            .distinct()
            .count()
            == 1
        )

        assert manager.filter(self_call_2__in=self_qs_1).distinct().count() == 1
        assert manager.filter(self_call_2_en__in=self_qs_1).count() == 0
        assert manager.filter(self_call_2_de__in=self_qs_1).distinct().count() == 1

        trans_real.activate("en")
        assert manager.filter(trans_through_model__in=testmodel_qs_1).distinct().count() == 1
        assert manager.filter(trans_through_model_de__in=testmodel_qs_1).count() == 0
        assert manager.filter(trans_through_model_en__in=testmodel_qs_1).distinct().count() == 1

        assert manager.filter(untrans__in=untranslated_qs).distinct().count() == 1
        assert manager.filter(untrans_de__in=untranslated_qs).count() == 0
        assert manager.filter(untrans_en__in=untranslated_qs).distinct().count() == 1

        assert manager.filter(self_call_1__in=self_qs_2).distinct().count() == 1
        assert manager.filter(self_call_1_de__in=self_qs_2).count() == 0
        assert manager.filter(self_call_1_en__in=self_qs_2).distinct().count() == 1

    def test_reverse_relations(self):
        models.TestModel.objects.bulk_create(
            models.TestModel(title_en="m2m_test_%s_en" % i, title_de="m2m_test_%s_de" % i)
            for i in range(10)
        )
        self.model.objects.bulk_create(
            self.model(title_en="m2m_test_%s_en" % i, title_de="m2m_test_%s_de" % i)
            for i in range(10)
        )
        models.NonTranslated.objects.bulk_create(
            models.NonTranslated(title="m2m_test_%s" % i) for i in range(10)
        )
        inst_both = self.model(title_en="inst_both_en", title_de="inst_both_de")
        inst_both.save()
        inst_en = self.model(title_en="inst_en_en", title_de="inst_en_de")
        inst_en.save()
        inst_de = self.model(title_en="inst_de_en", title_de="inst_de_de")
        inst_de.save()
        testmodel_qs = models.TestModel.objects.all()
        inst_both.test_en.set(testmodel_qs)
        inst_both.test_de.set(testmodel_qs)
        inst_en.test_en.set(testmodel_qs)
        inst_de.test_de.set(testmodel_qs)

        # Check that the reverse accessors are created on the model:
        # Explicit related_name
        testmodel_fields = get_field_names(models.TestModel)
        testmodel_methods = dir(models.TestModel)

        assert "m2m_test_ref" in testmodel_fields
        assert "m2m_test_ref_de" in testmodel_fields
        assert "m2m_test_ref_en" in testmodel_fields
        assert "m2m_test_ref" in testmodel_methods
        assert "m2m_test_ref_de" in testmodel_methods
        assert "m2m_test_ref_en" in testmodel_methods
        # Implicit related_name: manager descriptor name != query field name
        assert "customthroughmodel" in testmodel_fields
        assert "customthroughmodel_en" in testmodel_fields
        assert "customthroughmodel_de" in testmodel_fields
        assert "manytomanyfieldmodel_set" in testmodel_methods
        assert "manytomanyfieldmodel_en_set" in testmodel_methods
        assert "manytomanyfieldmodel_de_set" in testmodel_methods

        instance = models.TestModel.objects.first()
        # Check the German reverse accessor:
        assert inst_both in instance.m2m_test_ref_de.all()
        assert inst_de in instance.m2m_test_ref_de.all()
        assert inst_en not in instance.m2m_test_ref_de.all()

        # Check the English reverse accessor:
        assert inst_both in instance.m2m_test_ref_en.all()
        assert inst_en in instance.m2m_test_ref_en.all()
        assert inst_de not in instance.m2m_test_ref_en.all()

        # Check the default reverse accessor:
        trans_real.activate("de")
        assert inst_de in instance.m2m_test_ref.all()
        assert inst_en not in instance.m2m_test_ref.all()
        trans_real.activate("en")
        assert inst_en in instance.m2m_test_ref.all()
        assert inst_de not in instance.m2m_test_ref.all()

        # Check implicit related_name reverse accessor:
        inst_en.through_model.set(testmodel_qs)
        assert inst_en in instance.manytomanyfieldmodel_set.all()

        # Check filtering in reverse way + lookup spanning:

        manager = models.TestModel.objects
        trans_real.activate("de")
        assert manager.filter(m2m_test_ref__in=[inst_both]).count() == 10
        assert manager.filter(m2m_test_ref__in=[inst_de]).count() == 10
        assert manager.filter(m2m_test_ref__id__in=[inst_de.pk]).count() == 10
        assert manager.filter(m2m_test_ref__in=[inst_en]).count() == 0
        assert manager.filter(m2m_test_ref_en__in=[inst_en]).count() == 10
        assert manager.filter(manytomanyfieldmodel__in=[inst_en]).count() == 0
        assert manager.filter(manytomanyfieldmodel_en__in=[inst_en]).count() == 10
        assert manager.filter(m2m_test_ref__title="inst_de_de").distinct().count() == 10
        assert manager.filter(m2m_test_ref__title="inst_de_en").distinct().count() == 0
        assert manager.filter(m2m_test_ref__title_en="inst_de_en").distinct().count() == 10
        assert manager.filter(m2m_test_ref_en__title="inst_en_de").distinct().count() == 10

        trans_real.activate("en")
        assert manager.filter(m2m_test_ref__in=[inst_both]).count() == 10
        assert manager.filter(m2m_test_ref__in=[inst_en]).count() == 10
        assert manager.filter(m2m_test_ref__id__in=[inst_en.pk]).count() == 10
        assert manager.filter(m2m_test_ref__in=[inst_de]).count() == 0
        assert manager.filter(m2m_test_ref_de__in=[inst_de]).count() == 10
        assert manager.filter(manytomanyfieldmodel__in=[inst_en]).count() == 10
        assert manager.filter(manytomanyfieldmodel__in=[inst_de]).count() == 0
        assert manager.filter(manytomanyfieldmodel_de__in=[inst_de]).count() == 0
        assert manager.filter(m2m_test_ref__title="inst_en_en").distinct().count() == 10
        assert manager.filter(m2m_test_ref__title="inst_en_de").distinct().count() == 0
        assert manager.filter(m2m_test_ref__title_de="inst_en_de").distinct().count() == 10
        assert manager.filter(m2m_test_ref_de__title="inst_de_en").distinct().count() == 10


class OneToOneFieldsTest(ForeignKeyFieldsTest):
    @classmethod
    def setUpClass(cls):
        # 'model' attribute cannot be assigned to class in its definition,
        # because ``models`` module will be reloaded and hence class would use old model classes.
        super().setUpClass()
        cls.model = models.OneToOneFieldModel

    def test_uniqueness(self):
        instance1 = models.TestModel(title_en="title1_en", title_de="title1_de")
        instance1.save()
        inst = self.model()

        trans_real.activate("de")
        inst.test = instance1

        trans_real.activate("en")
        # That's ok, since test_en is different than test_de
        inst.test = instance1
        inst.save()

        # But this violates uniqueness constraint
        inst2 = self.model(test=instance1)
        with pytest.raises(IntegrityError):
            inst2.save()

    def test_reverse_relations(self):
        instance = models.TestModel(title_en="title_en", title_de="title_de")
        instance.save()

        # Instantiate many 'OneToOneFieldModel' instances:
        fk_inst_de = self.model(
            title_en="f_title_en", title_de="f_title_de", test_de_id=instance.pk
        )
        fk_inst_de.save()
        fk_inst_en = self.model(title_en="f_title_en", title_de="f_title_de", test_en=instance)
        fk_inst_en.save()

        fk_option_de = self.model.objects.create(optional_de=instance)
        fk_option_en = self.model.objects.create(optional_en=instance)

        # Check that the reverse accessors are created on the model:
        # Explicit related_name
        testmodel_fields = get_field_names(models.TestModel)
        testmodel_methods = dir(models.TestModel)
        assert "test_o2o" in testmodel_fields
        assert "test_o2o_de" in testmodel_fields
        assert "test_o2o_en" in testmodel_fields
        assert "test_o2o" in testmodel_methods
        assert "test_o2o_de" in testmodel_methods
        assert "test_o2o_en" in testmodel_methods
        # Implicit related_name
        assert "onetoonefieldmodel" in testmodel_fields
        assert "onetoonefieldmodel_de" in testmodel_fields
        assert "onetoonefieldmodel_en" in testmodel_fields
        assert "onetoonefieldmodel" in testmodel_methods
        assert "onetoonefieldmodel_de" in testmodel_methods
        assert "onetoonefieldmodel_en" in testmodel_methods

        # Check the German reverse accessor:
        assert fk_inst_de == instance.test_o2o_de

        # Check the English reverse accessor:
        assert fk_inst_en == instance.test_o2o_en

        # Check the default reverse accessor:
        trans_real.activate("de")
        assert fk_inst_de == instance.test_o2o
        trans_real.activate("en")
        assert fk_inst_en == instance.test_o2o

        # Check implicit related_name reverse accessor:
        assert fk_option_en == instance.onetoonefieldmodel

        # Check filtering in reverse way + lookup spanning:
        manager = models.TestModel.objects
        trans_real.activate("de")
        assert manager.filter(test_o2o=fk_inst_de).count() == 1
        assert manager.filter(test_o2o__id=fk_inst_de.pk).count() == 1
        assert manager.filter(test_o2o=fk_inst_en).count() == 0
        assert manager.filter(test_o2o_en=fk_inst_en).count() == 1
        assert manager.filter(onetoonefieldmodel=fk_option_de).count() == 1
        assert manager.filter(onetoonefieldmodel=fk_option_en).count() == 0
        assert manager.filter(onetoonefieldmodel_en=fk_option_en).count() == 1
        assert manager.filter(test_o2o__title="f_title_de").distinct().count() == 1
        assert manager.filter(test_o2o__title="f_title_en").distinct().count() == 0
        assert manager.filter(test_o2o__title_en="f_title_en").distinct().count() == 1
        trans_real.activate("en")
        assert manager.filter(test_o2o=fk_inst_en).count() == 1
        assert manager.filter(test_o2o__id=fk_inst_en.pk).count() == 1
        assert manager.filter(test_o2o=fk_inst_de).count() == 0
        assert manager.filter(test_o2o_de=fk_inst_de).count() == 1
        assert manager.filter(onetoonefieldmodel=fk_option_en).count() == 1
        assert manager.filter(onetoonefieldmodel=fk_option_de).count() == 0
        assert manager.filter(onetoonefieldmodel_de=fk_option_de).count() == 1
        assert manager.filter(test_o2o__title="f_title_en").distinct().count() == 1
        assert manager.filter(test_o2o__title="f_title_de").distinct().count() == 0
        assert manager.filter(test_o2o__title_de="f_title_de").distinct().count() == 1

        # Check assignment
        trans_real.activate("de")
        instance2 = models.TestModel(title_en="title_en", title_de="title_de")
        instance2.save()
        instance2.test_o2o = fk_inst_de
        instance2.test_o2o_en = fk_inst_en

        assert fk_inst_de.test.pk == instance2.pk
        assert fk_inst_de.test_id == instance2.pk
        assert fk_inst_de.test_de == instance2
        assert instance2.test_o2o_de == instance2.test_o2o
        assert fk_inst_de == instance2.test_o2o
        trans_real.activate("en")
        assert fk_inst_en.test.pk == instance2.pk
        assert fk_inst_en.test_id == instance2.pk
        assert fk_inst_en.test_en == instance2
        assert instance2.test_o2o_en == instance2.test_o2o
        assert fk_inst_en == instance2.test_o2o

    def test_non_translated_relation(self):
        non_de = models.NonTranslated.objects.create(title="title_de")
        non_en = models.NonTranslated.objects.create(title="title_en")

        fk_inst_de = self.model.objects.create(
            title_en="f_title_en", title_de="f_title_de", non_de=non_de
        )
        fk_inst_en = self.model.objects.create(
            title_en="f_title_en2", title_de="f_title_de2", non_en=non_en
        )

        # Forward relation + spanning
        manager = self.model.objects
        trans_real.activate("de")
        assert manager.filter(non=non_de).count() == 1
        assert manager.filter(non=non_en).count() == 0
        assert manager.filter(non_en=non_en).count() == 1
        assert manager.filter(non__title="title_de").count() == 1
        assert manager.filter(non__title="title_en").count() == 0
        assert manager.filter(non_en__title="title_en").count() == 1
        trans_real.activate("en")
        assert manager.filter(non=non_en).count() == 1
        assert manager.filter(non=non_de).count() == 0
        assert manager.filter(non_de=non_de).count() == 1
        assert manager.filter(non__title="title_en").count() == 1
        assert manager.filter(non__title="title_de").count() == 0
        assert manager.filter(non_de__title="title_de").count() == 1

        # Reverse relation + spanning
        manager = models.NonTranslated.objects
        trans_real.activate("de")
        assert manager.filter(test_o2o=fk_inst_de).count() == 1
        assert manager.filter(test_o2o=fk_inst_en).count() == 0
        assert manager.filter(test_o2o_en=fk_inst_en).count() == 1
        assert manager.filter(test_o2o__title="f_title_de").count() == 1
        assert manager.filter(test_o2o__title="f_title_en").count() == 0
        assert manager.filter(test_o2o__title_en="f_title_en").count() == 1
        trans_real.activate("en")
        assert manager.filter(test_o2o=fk_inst_en).count() == 1
        assert manager.filter(test_o2o=fk_inst_de).count() == 0
        assert manager.filter(test_o2o_de=fk_inst_de).count() == 1
        assert manager.filter(test_o2o__title="f_title_en2").count() == 1
        assert manager.filter(test_o2o__title="f_title_de2").count() == 0
        assert manager.filter(test_o2o__title_de="f_title_de2").count() == 1


class OtherFieldsTest(ModeltranslationTestBase):
    def test_translated_models(self):
        inst = models.OtherFieldsModel.objects.create()
        field_names = dir(inst)
        assert "id" in field_names
        assert "int" in field_names
        assert "int_de" in field_names
        assert "int_en" in field_names
        assert "boolean" in field_names
        assert "boolean_de" in field_names
        assert "boolean_en" in field_names
        assert "genericip" in field_names
        assert "genericip_de" in field_names
        assert "genericip_en" in field_names
        assert "float" in field_names
        assert "float_de" in field_names
        assert "float_en" in field_names
        assert "decimal" in field_names
        assert "decimal_de" in field_names
        assert "decimal_en" in field_names
        assert "json" in field_names
        assert "json_de" in field_names
        assert "json_en" in field_names
        inst.delete()

    def test_translated_models_integer_instance(self):
        inst = models.OtherFieldsModel()
        inst.int = 7
        assert "de" == get_language()
        assert 7 == inst.int
        assert 7 == inst.int_de
        assert 42 == inst.int_en  # default value is honored

        inst.int += 2
        inst.save()
        assert 9 == inst.int
        assert 9 == inst.int_de
        assert 42 == inst.int_en

        trans_real.activate("en")
        inst.int -= 1
        assert 41 == inst.int
        assert 9 == inst.int_de
        assert 41 == inst.int_en

        # this field has validator - let's try to make it below 0!
        inst.int -= 50
        with pytest.raises(ValidationError):
            inst.full_clean()

    def test_translated_models_boolean_instance(self):
        inst = models.OtherFieldsModel()
        inst.boolean = True
        assert "de" == get_language()
        assert inst.boolean is True
        assert inst.boolean_de is True
        assert inst.boolean_en is False

        inst.boolean = False
        inst.save()
        assert inst.boolean is False
        assert inst.boolean_de is False
        assert inst.boolean_en is False

        trans_real.activate("en")
        inst.boolean = True
        assert inst.boolean is True
        assert inst.boolean_de is False
        assert inst.boolean_en is True

    def test_translated_models_genericipaddress_instance(self):
        inst = models.OtherFieldsModel()
        inst.genericip = "2a02:42fe::4"
        assert "de" == get_language()
        assert "2a02:42fe::4" == inst.genericip
        assert "2a02:42fe::4" == inst.genericip_de
        assert inst.genericip_en is None

        inst.genericip = "2a02:23fe::4"
        inst.save()
        assert "2a02:23fe::4" == inst.genericip
        assert "2a02:23fe::4" == inst.genericip_de
        assert inst.genericip_en is None

        trans_real.activate("en")
        inst.genericip = "2a02:42fe::4"
        assert "2a02:42fe::4" == inst.genericip
        assert "2a02:23fe::4" == inst.genericip_de
        assert "2a02:42fe::4" == inst.genericip_en

        # Check if validation is preserved
        inst.genericip = "1;2"
        with pytest.raises(ValidationError):
            inst.full_clean()

    def test_translated_models_float_instance(self):
        inst = models.OtherFieldsModel()
        inst.float = 0.42
        assert "de" == get_language()
        assert 0.42 == inst.float
        assert 0.42 == inst.float_de
        assert inst.float_en is None

        inst.float = 0.23
        inst.save()
        assert 0.23 == inst.float
        assert 0.23 == inst.float_de
        assert inst.float_en is None

        inst.float += 0.08
        assert 0.31 == inst.float
        assert 0.31 == inst.float_de
        assert inst.float_en is None

        trans_real.activate("en")
        inst.float = 0.42
        assert 0.42 == inst.float
        assert 0.31 == inst.float_de
        assert 0.42 == inst.float_en

    def test_translated_models_decimal_instance(self):
        inst = models.OtherFieldsModel()
        inst.decimal = Decimal("0.42")
        assert "de" == get_language()
        assert Decimal("0.42") == inst.decimal
        assert Decimal("0.42") == inst.decimal_de
        assert inst.decimal_en is None

        inst.decimal = inst.decimal - Decimal("0.19")
        inst.save()
        assert Decimal("0.23") == inst.decimal
        assert Decimal("0.23") == inst.decimal_de
        assert inst.decimal_en is None

        trans_real.activate("en")
        with pytest.raises(TypeError):
            inst.decimal + Decimal("0.19")
        assert inst.decimal is None
        assert Decimal("0.23") == inst.decimal_de
        assert inst.decimal_en is None

        inst.decimal = Decimal("0.42")
        assert Decimal("0.42") == inst.decimal
        assert Decimal("0.23") == inst.decimal_de
        assert Decimal("0.42") == inst.decimal_en

    def test_translated_models_date_instance(self):
        inst = models.OtherFieldsModel()
        inst.date = datetime.date(2012, 12, 31)
        assert "de" == get_language()
        assert datetime.date(2012, 12, 31) == inst.date
        assert datetime.date(2012, 12, 31) == inst.date_de
        assert inst.date_en is None

        inst.date = datetime.date(1999, 1, 1)
        inst.save()
        assert datetime.date(1999, 1, 1) == inst.date
        assert datetime.date(1999, 1, 1) == inst.date_de
        assert inst.date_en is None

        qs = models.OtherFieldsModel.objects.filter(date="1999-1-1")
        assert len(qs) == 1
        assert qs[0].date == datetime.date(1999, 1, 1)

        trans_real.activate("en")
        inst.date = datetime.date(2012, 12, 31)
        assert datetime.date(2012, 12, 31) == inst.date
        assert datetime.date(1999, 1, 1) == inst.date_de
        assert datetime.date(2012, 12, 31) == inst.date_en

    def test_translated_models_datetime_instance(self):
        inst = models.OtherFieldsModel()
        inst.datetime = datetime.datetime(2012, 12, 31, 23, 42)
        assert "de" == get_language()
        assert datetime.datetime(2012, 12, 31, 23, 42) == inst.datetime
        assert datetime.datetime(2012, 12, 31, 23, 42) == inst.datetime_de
        assert inst.datetime_en is None

        inst.datetime = datetime.datetime(1999, 1, 1, 23, 42)
        inst.save()
        assert datetime.datetime(1999, 1, 1, 23, 42) == inst.datetime
        assert datetime.datetime(1999, 1, 1, 23, 42) == inst.datetime_de
        assert inst.datetime_en is None

        qs = models.OtherFieldsModel.objects.filter(datetime="1999-1-1 23:42")
        assert len(qs) == 1
        assert qs[0].datetime == datetime.datetime(1999, 1, 1, 23, 42)

        trans_real.activate("en")
        inst.datetime = datetime.datetime(2012, 12, 31, 23, 42)
        assert datetime.datetime(2012, 12, 31, 23, 42) == inst.datetime
        assert datetime.datetime(1999, 1, 1, 23, 42) == inst.datetime_de
        assert datetime.datetime(2012, 12, 31, 23, 42) == inst.datetime_en

    def test_translated_models_time_instance(self):
        inst = models.OtherFieldsModel()
        inst.time = datetime.time(23, 42, 0)
        assert "de" == get_language()
        assert datetime.time(23, 42, 0) == inst.time
        assert datetime.time(23, 42, 0) == inst.time_de
        assert inst.time_en is None

        inst.time = datetime.time(1, 2, 3)
        inst.save()
        assert datetime.time(1, 2, 3) == inst.time
        assert datetime.time(1, 2, 3) == inst.time_de
        assert inst.time_en is None

        qs = models.OtherFieldsModel.objects.filter(time="01:02:03")
        assert len(qs) == 1
        assert qs[0].time == datetime.time(1, 2, 3)

        trans_real.activate("en")
        inst.time = datetime.time(23, 42, 0)
        assert datetime.time(23, 42, 0) == inst.time
        assert datetime.time(1, 2, 3) == inst.time_de
        assert datetime.time(23, 42, 0) == inst.time_en

    def test_dates_queryset(self):
        Model = models.OtherFieldsModel

        Model.objects.create(datetime=datetime.datetime(2015, 9, 2, 0, 0))
        Model.objects.create(datetime=datetime.datetime(2014, 8, 3, 0, 0))
        Model.objects.create(datetime=datetime.datetime(2013, 7, 4, 0, 0))

        qs = Model.objects.dates("datetime", "year", "DESC")

        assert list(qs) == [
            datetime.date(2015, 1, 1),
            datetime.date(2014, 1, 1),
            datetime.date(2013, 1, 1),
        ]

    def test_descriptors(self):
        # Descriptor store ints in database and returns string of 'a' of that length
        inst = models.DescriptorModel()
        # Demonstrate desired behaviour
        inst.normal = 2
        assert "aa" == inst.normal
        inst.normal = "abc"
        assert "aaa" == inst.normal

        # Descriptor on translated field works too
        assert "de" == get_language()
        inst.trans = 5
        assert "aaaaa" == inst.trans

        inst.save()
        db_values = models.DescriptorModel.objects.raw_values("normal", "trans_en", "trans_de")[0]
        assert 3 == db_values["normal"]
        assert 5 == db_values["trans_de"]
        assert 0 == db_values["trans_en"]

        # Retrieval from db
        inst = models.DescriptorModel.objects.all()[0]
        assert "aaa" == inst.normal
        assert "aaaaa" == inst.trans
        assert "aaaaa" == inst.trans_de
        assert "" == inst.trans_en

        # Other language
        trans_real.activate("en")
        assert "" == inst.trans
        inst.trans = "q"
        assert "a" == inst.trans
        inst.trans_de = 4
        assert "aaaa" == inst.trans_de
        inst.save()
        db_values = models.DescriptorModel.objects.raw_values("normal", "trans_en", "trans_de")[0]
        assert 3 == db_values["normal"]
        assert 4 == db_values["trans_de"]
        assert 1 == db_values["trans_en"]


class ModeltranslationTestRule1(ModeltranslationTestBase):
    """
    Rule 1: Reading the value from the original field returns the value in
    translated to the current language.
    """

    def _test_field(self, field_name, value_de, value_en, deactivate=True):
        field_name_de = "%s_de" % field_name
        field_name_en = "%s_en" % field_name
        params = {field_name_de: value_de, field_name_en: value_en}

        n = models.TestModel.objects.create(**params)
        trans_real.activate("de")
        # Language is set to 'de' at this point
        assert get_language() == "de"
        assert getattr(n, field_name) == value_de
        assert getattr(n, field_name_de) == value_de
        assert getattr(n, field_name_en) == value_en
        # Now switch to "en"
        trans_real.activate("en")
        assert get_language() == "en"
        # Should now be return the english one (just by switching the language)
        assert getattr(n, field_name) == value_en
        # But explicit language fields hold their values
        assert getattr(n, field_name_de) == value_de
        assert getattr(n, field_name_en) == value_en

        n = models.TestModel.objects.create(**params)
        n.save()
        # Language is set to "en" at this point
        assert get_language() == "en"
        assert getattr(n, field_name) == value_en
        assert getattr(n, field_name_de) == value_de
        assert getattr(n, field_name_en) == value_en
        trans_real.activate("de")
        assert get_language() == "de"
        assert getattr(n, field_name) == value_de

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

        self._test_field(field_name="title", value_de=title1_de, value_en=title1_en)
        self._test_field(field_name="text", value_de=text_de, value_en=text_en)

    def test_rule1_url_field(self):
        self._test_field(
            field_name="url", value_de="http://www.google.de", value_en="http://www.google.com"
        )

    def test_rule1_email_field(self):
        self._test_field(
            field_name="email",
            value_de="django-modeltranslation@googlecode.de",
            value_en="django-modeltranslation@googlecode.com",
        )


class ModeltranslationTestRule2(ModeltranslationTestBase):
    """
    Rule 2: Assigning a value to the original field updates the value
    in the associated current language translation field.
    """

    def _test_field(self, field_name, value1_de, value1_en, value2, value3, deactivate=True):
        field_name_de = "%s_de" % field_name
        field_name_en = "%s_en" % field_name
        params = {field_name_de: value1_de, field_name_en: value1_en}

        assert get_language() == "de"
        n = models.TestModel.objects.create(**params)
        assert getattr(n, field_name) == value1_de
        assert getattr(n, field_name_de) == value1_de
        assert getattr(n, field_name_en) == value1_en

        setattr(n, field_name, value2)
        n.save()
        assert getattr(n, field_name) == value2
        assert getattr(n, field_name_de) == value2
        assert getattr(n, field_name_en) == value1_en

        trans_real.activate("en")
        assert get_language() == "en"

        setattr(n, field_name, value3)
        setattr(n, field_name_de, value1_de)
        n.save()
        assert getattr(n, field_name) == value3
        assert getattr(n, field_name_en) == value3
        assert getattr(n, field_name_de) == value1_de

        if deactivate:
            trans_real.deactivate()

    def test_rule2(self):
        """
        Basic CharField/TextField test.
        """
        self._test_field(
            field_name="title",
            value1_de="title de",
            value1_en="title en",
            value2="Neuer Titel",
            value3="new title",
        )

    def test_rule2_url_field(self):
        self._test_field(
            field_name="url",
            value1_de="http://www.google.de",
            value1_en="http://www.google.com",
            value2="http://www.google.at",
            value3="http://www.google.co.uk",
        )

    def test_rule2_email_field(self):
        self._test_field(
            field_name="email",
            value1_de="django-modeltranslation@googlecode.de",
            value1_en="django-modeltranslation@googlecode.com",
            value2="django-modeltranslation@googlecode.at",
            value3="django-modeltranslation@googlecode.co.uk",
        )


class ModeltranslationTestRule3(ModeltranslationTestBase):
    """
    Rule 3: If both fields - the original and the current language translation
    field - are updated at the same time, the current language translation
    field wins.
    """

    def test_rule3(self):
        assert get_language() == "de"
        title = "title de"

        # Normal behaviour
        n = models.TestModel(title="foo")
        assert n.title == "foo"
        assert n.title_de == "foo"
        assert n.title_en is None

        # constructor
        n = models.TestModel(title_de=title, title="foo")
        assert n.title == title
        assert n.title_de == title
        assert n.title_en is None

        # object.create
        n = models.TestModel.objects.create(title_de=title, title="foo")
        assert n.title == title
        assert n.title_de == title
        assert n.title_en is None

        # Database save/load
        n = models.TestModel.objects.get(title_de=title)
        assert n.title == title
        assert n.title_de == title
        assert n.title_en is None

        # This is not subject to Rule 3, because updates are not *at the ame time*
        n = models.TestModel()
        n.title_de = title
        n.title = "foo"
        assert n.title == "foo"
        assert n.title_de == "foo"
        assert n.title_en is None

    @staticmethod
    def _index(list, element):
        for i, el in enumerate(list):
            if el is element:
                return i
        raise ValueError

    def test_rule3_internals(self):
        # Rule 3 work because translation fields are added to model field list
        # later than original field.
        original = models.TestModel._meta.get_field("title")
        translated_de = models.TestModel._meta.get_field("title_de")
        translated_en = models.TestModel._meta.get_field("title_en")
        fields = models.TestModel._meta.fields
        # Here we cannot use simple list.index, because Field has overloaded __cmp__
        assert self._index(fields, original) < self._index(fields, translated_de)
        assert self._index(fields, original) < self._index(fields, translated_en)


class ModelValidationTest(ModeltranslationTestBase):
    """
    Tests if a translation model field validates correctly.
    """

    def assertRaisesValidation(self, func):
        try:
            func()
        except ValidationError as e:
            return e.message_dict
        self.fail("ValidationError not raised.")

    def _test_model_validation(self, field_name, invalid_value, valid_value):
        """
        Generic model field validation test.
        """
        field_name_de = "%s_de" % field_name
        field_name_en = "%s_en" % field_name
        # Title need to be passed here - otherwise it would not validate
        params = {"title_de": "title de", "title_en": "title en", field_name: invalid_value}

        n = models.TestModel.objects.create(**params)

        # First check the original field
        # Expect that the validation object contains an error
        errors = self.assertRaisesValidation(n.full_clean)
        assert field_name in errors

        # Set translation field to a valid value
        # Language is set to 'de' at this point
        assert get_language() == "de"
        setattr(n, field_name_de, valid_value)
        n.full_clean()

        # All language fields are validated even though original field validation raise no error
        setattr(n, field_name_en, invalid_value)
        errors = self.assertRaisesValidation(n.full_clean)
        assert field_name not in errors
        assert field_name_en in errors

        # When language is changed to en, the original field also doesn't validate
        with override("en"):
            setattr(n, field_name_en, invalid_value)
            errors = self.assertRaisesValidation(n.full_clean)
            assert field_name in errors
            assert field_name_en in errors

        # Set translation field to an invalid value
        setattr(n, field_name_en, valid_value)
        setattr(n, field_name_de, invalid_value)
        # Expect that the validation object contains an error for url_de
        errors = self.assertRaisesValidation(n.full_clean)
        assert field_name in errors
        assert field_name_de in errors

    def test_model_validation_required(self):
        """
        General test for CharField: if required/blank is handled properly.
        """
        # Create an object without title (which is required)
        n = models.TestModel.objects.create(text="Testtext")

        # First check the original field
        # Expect that the validation object contains an error for title
        errors = self.assertRaisesValidation(n.full_clean)
        assert "title" in errors
        n.save()

        # Check the translation field
        # Language is set to 'de' at this point
        assert get_language() == "de"
        # Set translation field to a valid title
        n.title_de = "Title"
        n.full_clean()

        # Change language to en
        # Now validation fails, because current language (en) title is empty
        # So requirement validation depends on current language
        with override("en"):
            errors = self.assertRaisesValidation(n.full_clean)
            assert "title" in errors

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
        assert "title_de" not in errors
        assert "title" in errors

    def test_model_validation_url_field(self):
        self._test_model_validation(
            field_name="url",
            invalid_value="foo en",
            valid_value="http://code.google.com/p/django-modeltranslation/",
        )

    def test_model_validation_email_field(self):
        self._test_model_validation(
            field_name="email",
            invalid_value="foo en",
            valid_value="django-modeltranslation@googlecode.com",
        )


class ModelInheritanceTest(ModeltranslationTestBase):
    """Tests for inheritance support in modeltranslation."""

    def test_abstract_inheritance(self):
        field_names_b = get_field_names(models.AbstractModelB)
        assert "titlea" in field_names_b
        assert "titlea_de" in field_names_b
        assert "titlea_en" in field_names_b
        assert "titleb" in field_names_b
        assert "titleb_de" in field_names_b
        assert "titleb_en" in field_names_b
        assert "titled" not in field_names_b
        assert "titled_de" not in field_names_b
        assert "titled_en" not in field_names_b

    def test_multitable_inheritance(self):
        field_names_a = get_field_names(models.MultitableModelA)
        assert "titlea" in field_names_a
        assert "titlea_de" in field_names_a
        assert "titlea_en" in field_names_a

        field_names_b = get_field_names(models.MultitableModelB)
        assert "titlea" in field_names_b
        assert "titlea_de" in field_names_b
        assert "titlea_en" in field_names_b
        assert "titleb" in field_names_b
        assert "titleb_de" in field_names_b
        assert "titleb_en" in field_names_b

        field_names_c = get_field_names(models.MultitableModelC)
        assert "titlea" in field_names_c
        assert "titlea_de" in field_names_c
        assert "titlea_en" in field_names_c
        assert "titleb" in field_names_c
        assert "titleb_de" in field_names_c
        assert "titleb_en" in field_names_c
        assert "titlec" in field_names_c
        assert "titlec_de" in field_names_c
        assert "titlec_en" in field_names_c

        field_names_d = get_field_names(models.MultitableModelD)
        assert "titlea" in field_names_d
        assert "titlea_de" in field_names_d
        assert "titlea_en" in field_names_d
        assert "titleb" in field_names_d
        assert "titleb_de" in field_names_d
        assert "titleb_en" in field_names_d
        assert "titled" in field_names_d

    def test_inheritance(self):
        def assertLocalFields(model, local_fields):
            # Proper fields are inherited.
            opts = translator.translator.get_options_for_model(model)
            assert set(opts.local_fields.keys()) == set(local_fields)
            # Local translation fields are created on the model.
            model_local_fields = [f.name for f in model._meta.local_fields]
            for field in local_fields:
                for lang in mt_settings.AVAILABLE_LANGUAGES:
                    translation_field = build_localized_fieldname(field, lang)
                    assert translation_field in model_local_fields

        def assertFields(model, fields):
            # The given fields are inherited.
            opts = translator.translator.get_options_for_model(model)
            assert set(opts.all_fields.keys()) == set(fields)
            # Inherited translation fields are available on the model.
            model_fields = get_field_names(model)
            for field in fields:
                for lang in mt_settings.AVAILABLE_LANGUAGES:
                    translation_field = build_localized_fieldname(field, lang)
                    assert translation_field in model_fields

        # Translation fields can be declared on abstract classes.
        assertLocalFields(models.Slugged, ("slug",))
        assertLocalFields(models.MetaData, ("keywords",))
        assertLocalFields(models.RichText, ("content",))
        # Local fields are inherited from abstract superclasses.
        assertLocalFields(
            models.Displayable,
            (
                "slug",
                "keywords",
            ),
        )
        assertLocalFields(
            models.Page,
            (
                "slug",
                "keywords",
                "title",
            ),
        )
        # But not from concrete superclasses.
        assertLocalFields(models.RichTextPage, ("content",))

        # Fields inherited from concrete models are also available.
        assertFields(models.Slugged, ("slug",))
        assertFields(
            models.Page,
            (
                "slug",
                "keywords",
                "title",
            ),
        )
        assertFields(
            models.RichTextPage,
            (
                "slug",
                "keywords",
                "title",
                "content",
            ),
        )


class ModelInheritanceFieldAggregationTest(ModeltranslationTestBase):
    """
    Tests for inheritance support with field aggregation
    in modeltranslation.
    """

    def test_field_aggregation(self):
        clsb = translation.FieldInheritanceCTranslationOptions
        assert "titlea" in clsb.fields
        assert "titleb" in clsb.fields
        assert "titlec" in clsb.fields
        assert 3 == len(clsb.fields)
        assert isinstance(clsb.fields, tuple)

    def test_multi_inheritance(self):
        clsb = translation.FieldInheritanceETranslationOptions
        assert "titlea" in clsb.fields
        assert "titleb" in clsb.fields
        assert "titlec" in clsb.fields
        assert "titled" in clsb.fields
        assert "titlee" in clsb.fields
        assert 5 == len(clsb.fields)  # there are no repetitions


class UpdateCommandTest(ModeltranslationTestBase):
    def test_update_command(self):
        # Here it would be convenient to use fixtures - unfortunately,
        # fixtures loader doesn't use raw sql but rather creates objects,
        # so translation descriptor affects result and we cannot set the
        # 'original' field value.
        pk1 = models.TestModel.objects.create(title_de="").pk
        pk2 = models.TestModel.objects.create(title_de="already").pk
        # Due to ``rewrite(False)`` here, original field will be affected.
        models.TestModel.objects.all().rewrite(False).update(title="initial")

        # Check raw data using ``values``
        obj1 = models.TestModel.objects.filter(pk=pk1).raw_values()[0]
        obj2 = models.TestModel.objects.filter(pk=pk2).raw_values()[0]
        assert "" == obj1["title_de"]
        assert "initial" == obj1["title"]
        assert "already" == obj2["title_de"]
        assert "initial" == obj2["title"]

        call_command("update_translation_fields", "tests", verbosity=0)

        obj1 = models.TestModel.objects.get(pk=pk1)
        obj2 = models.TestModel.objects.get(pk=pk2)
        assert "initial" == obj1.title_de
        assert "already" == obj2.title_de

    def test_update_command_language_param(self):
        trans_real.activate("en")
        pk1 = models.TestModel.objects.create(title_en="").pk
        pk2 = models.TestModel.objects.create(title_en="already").pk
        # Due to ``rewrite(False)`` here, original field will be affected.
        models.TestModel.objects.all().rewrite(False).update(title="initial")

        call_command("update_translation_fields", "tests", language="en", verbosity=0)

        obj1 = models.TestModel.objects.get(pk=pk1)
        obj2 = models.TestModel.objects.get(pk=pk2)
        assert "initial" == obj1.title_en
        assert "already" == obj2.title_en

    def test_update_command_invalid_language_param(self):
        with pytest.raises(CommandError):
            call_command("update_translation_fields", language="xx", verbosity=0)

    def test_update_command_with_json_field(self):
        """
        Test that the update_translation_fields command works with JSON fields.
        """
        instance_pk = models.OtherFieldsModel.objects.create(json={"foo": "bar"}).pk
        models.OtherFieldsModel.objects.all().rewrite(False).update(json_de=None)

        instance = models.OtherFieldsModel.objects.filter(pk=instance_pk).raw_values()[0]

        assert instance["json"] == {"foo": "bar"}
        assert instance["json_de"] is None
        assert instance["json_en"] is None

        call_command(
            "update_translation_fields", "tests", model_name="OtherFieldsModel", verbosity=0
        )

        instance = models.OtherFieldsModel.objects.filter(pk=instance_pk).raw_values()[0]

        assert instance["json"] == {"foo": "bar"}
        assert instance["json_de"] == {"foo": "bar"}
        assert instance["json_en"] is None


class TestManager(ModeltranslationTestBase):
    def setUp(self):
        # In this test case the default language is en, not de.
        super().setUp()
        trans_real.activate("en")

    def test_filter_update(self):
        """Test if filtering and updating is language-aware."""
        n = models.ManagerTestModel(title="")
        n.title_en = "en"
        n.title_de = "de"
        n.save()

        m = models.ManagerTestModel(title="")
        m.title_en = "title en"
        m.title_de = "de"
        m.save()

        assert "en" == get_language()

        assert 0 == models.ManagerTestModel.objects.filter(title="de").count()
        assert 1 == models.ManagerTestModel.objects.filter(title="en").count()
        # Spanning works
        assert 2 == models.ManagerTestModel.objects.filter(title__contains="en").count()

        with override("de"):
            assert 2 == models.ManagerTestModel.objects.filter(title="de").count()
            assert 0 == models.ManagerTestModel.objects.filter(title="en").count()
            # Spanning works
            assert 2 == models.ManagerTestModel.objects.filter(title__endswith="e").count()

            # Still possible to use explicit language version
            assert 1 == models.ManagerTestModel.objects.filter(title_en="en").count()
            assert 2 == models.ManagerTestModel.objects.filter(title_en__contains="en").count()

            models.ManagerTestModel.objects.update(title="new")
            assert 2 == models.ManagerTestModel.objects.filter(title="new").count()
            n = models.ManagerTestModel.objects.get(pk=n.pk)
            m = models.ManagerTestModel.objects.get(pk=m.pk)
            assert "en" == n.title_en
            assert "new" == n.title_de
            assert "title en" == m.title_en
            assert "new" == m.title_de

        # Test Python3 "dictionary changed size during iteration"
        assert 1 == models.ManagerTestModel.objects.filter(title="en", title_en="en").count()

    def test_q(self):
        """Test if Q queries are rewritten."""
        n = models.ManagerTestModel(title="")
        n.title_en = "en"
        n.title_de = "de"
        n.save()

        assert "en" == get_language()
        assert 0 == models.ManagerTestModel.objects.filter(Q(title="de") | Q(pk=42)).count()
        assert 1 == models.ManagerTestModel.objects.filter(Q(title="en") | Q(pk=42)).count()

        with override("de"):
            assert 1 == models.ManagerTestModel.objects.filter(Q(title="de") | Q(pk=42)).count()
            assert 0 == models.ManagerTestModel.objects.filter(Q(title="en") | Q(pk=42)).count()

    def test_f(self):
        """Test if F queries are rewritten."""
        n = models.ManagerTestModel.objects.create(visits_en=1, visits_de=2)

        assert "en" == get_language()
        models.ManagerTestModel.objects.update(visits=F("visits") + 10)
        n = models.ManagerTestModel.objects.all()[0]
        assert n.visits_en == 11
        assert n.visits_de == 2

        with override("de"):
            models.ManagerTestModel.objects.update(visits=F("visits") + 20)
            n = models.ManagerTestModel.objects.all()[0]
            assert n.visits_en == 11
            assert n.visits_de == 22

    def test_order_by(self):
        """Check that field names are rewritten in order_by keys."""
        manager = models.ManagerTestModel.objects
        manager.create(title="a")
        m = manager.create(title="b")
        manager.create(title="c")
        with override("de"):
            # Make the order of the 'title' column different.
            m.title = "d"
            m.save()
        titles_asc = tuple(m.title for m in manager.order_by("title"))
        titles_desc = tuple(m.title for m in manager.order_by("-title"))
        assert titles_asc == ("a", "b", "c")
        assert titles_desc == ("c", "b", "a")

    def test_order_by_meta(self):
        """Check that meta ordering is rewritten."""
        manager = models.ManagerTestModel.objects
        manager.create(title="more_de", visits_en=1, visits_de=2)
        manager.create(title="more_en", visits_en=2, visits_de=1)
        manager.create(title="most", visits_en=3, visits_de=3)
        manager.create(title="least", visits_en=0, visits_de=0)

        # Ordering descending with visits_en
        titles_for_en = tuple(m.title_en for m in manager.all())
        with override("de"):
            # Ordering descending with visits_de
            titles_for_de = tuple(m.title_en for m in manager.all())

        assert titles_for_en == ("most", "more_en", "more_de", "least")
        assert titles_for_de == ("most", "more_de", "more_en", "least")

    def test_order_by_reset(self):
        qs = models.ManagerTestModel.objects.all()
        assert qs.ordered
        assert not qs.order_by().ordered
        assert not qs.values("title").order_by().ordered
        assert not qs.order_by().values("title").ordered, "queryset is unexpectedly ordered"

    def test_latest(self):
        manager = models.ManagerTestModel.objects
        manager.create(title="more_de", visits_en=1, visits_de=2)
        instance_2 = manager.create(title="more_en", visits_en=2, visits_de=1)
        lainstanceance = manager.latest("id")
        assert lainstanceance == instance_2

    def assert_fallback(self, method, expected1, *args, **kwargs):
        transform = kwargs.pop("transform", lambda x: x)
        expected2 = kwargs.pop("expected_de", expected1)
        with default_fallback():
            # Fallback is ('de',)
            obj = method(*args, **kwargs)[0]
            with override("de"):
                obj2 = method(*args, **kwargs)[0]
        assert transform(obj) == expected1
        assert transform(obj2) == expected2

    def test_values_fallback(self):
        manager = models.ManagerTestModel.objects
        manager.create(title_en="", title_de="de")
        assert "en" == get_language()

        self.assert_fallback(manager.values, "de", "title", transform=lambda x: x["title"])
        self.assert_fallback(manager.values_list, "de", "title", flat=True)
        self.assert_fallback(manager.values_list, ("de", "", "de"), "title", "title_en", "title_de")

        # Settings are taken into account - fallback can be disabled
        with override_settings(MODELTRANSLATION_ENABLE_FALLBACKS=False):
            self.assert_fallback(
                manager.values, "", "title", expected_de="de", transform=lambda x: x["title"]
            )

        # Test fallback values
        manager = models.FallbackModel.objects
        manager.create()

        self.assert_fallback(manager.values, "fallback", "title", transform=lambda x: x["title"])
        self.assert_fallback(manager.values_list, ("fallback", "fallback"), "title", "text")

    def test_values(self):
        manager = models.ManagerTestModel.objects
        id1 = manager.create(title_en="en", title_de="de").pk

        raw_obj = manager.raw_values("title")[0]
        obj = manager.values("title")[0]
        with override("de"):
            raw_obj2 = manager.raw_values("title")[0]
            obj2 = manager.values("title")[0]

        # Raw_values returns real database values regardless of current language
        assert raw_obj["title"] == raw_obj2["title"]
        # Values present language-aware data, from the moment of retrieval
        assert obj["title"] == "en"
        assert obj2["title"] == "de"

        # Values_list behave similarly
        assert list(manager.values_list("title", flat=True)) == ["en"]
        with override("de"):
            assert list(manager.values_list("title", flat=True)) == ["de"]

        # Values_list with named fields behave similarly.
        # Also, it should preserve requested ordering.
        (actual,) = manager.annotate(annotated=Value(True)).values_list(
            "title", "annotated", "visits", named=True
        )
        expected = ("en", True, 0)
        assert actual == expected
        assert (actual.title, actual.annotated, actual.visits) == expected
        with override("de"):
            assert list(manager.values_list("title", "visits", named=True)) == [("de", 0)]

        # One can always turn rewrite off
        a = list(manager.rewrite(False).values_list("title", flat=True))
        with override("de"):
            b = list(manager.rewrite(False).values_list("title", flat=True))
        assert a == b

        i2 = manager.create(title_en="en2", title_de="de2")
        id2 = i2.pk

        # This is somehow repetitive...
        assert "en" == get_language()
        assert list(manager.values("title")) == [{"title": "en"}, {"title": "en2"}]
        with override("de"):
            assert list(manager.values("title")) == [{"title": "de"}, {"title": "de2"}]

        # When no fields are passed, list all fields in current language.
        actual = list(manager.annotate(annotated=Value(True)).values())
        assert actual == [
            {"id": id1, "title": "en", "visits": 0, "description": None, "annotated": True},
            {"id": id2, "title": "en2", "visits": 0, "description": None, "annotated": True},
        ]
        # Similar for values_list
        assert list(manager.values_list()) == [(id1, "en", 0, None), (id2, "en2", 0, None)]
        with override("de"):
            assert list(manager.values_list()) == [(id1, "de", 0, None), (id2, "de2", 0, None)]

        # Raw_values
        assert list(manager.raw_values()) == list(manager.rewrite(False).values())
        i2.delete()
        assert list(manager.raw_values()) == [
            {
                "id": id1,
                "title": "en",
                "title_en": "en",
                "title_de": "de",
                "visits": 0,
                "visits_en": 0,
                "visits_de": 0,
                "description": None,
                "description_en": None,
                "description_de": None,
            },
        ]

        # annotation issue (#374)
        assert list(manager.values_list("title", flat=True).annotate(Count("title"))) == ["en"]

        # custom annotation
        assert list(manager.filter(id=id1).annotate(custom_id=F("id")).values_list())[0][-1] == id1
        assert (
            list(manager.filter(id=id1).annotate(custom_id=F("id")).values())[0].get("custom_id")
            == id1
        )

        # custom annotation with fields specified
        assert list(manager.filter(id=id1).annotate(custom_id=F("id")).values_list("id"))[0] == (
            id1,
        )
        assert (
            list(manager.filter(id=id1).annotate(custom_id=F("id")).values("id"))[0].get(
                "custom_id"
            )
            is None
        )

    def test_values_list_annotation(self):
        models.TestModel(title="foo").save()
        models.TestModel(title="foo").save()
        assert list(models.TestModel.objects.all().values_list("title").annotate(Count("id"))) == [
            ("foo", 2)
        ]

    def test_values_with_expressions(self):
        manager = models.ManagerTestModel.objects
        id1 = manager.create(title_en="en", title_de="de").pk

        raw_obj = manager.raw_values("title", str_pk=Cast("pk", output_field=CharField()))[0]
        obj = manager.values("title", str_pk=Cast("pk", output_field=CharField()))[0]
        with override("de"):
            raw_obj2 = manager.raw_values("title", str_pk=Cast("pk", output_field=CharField()))[0]
            obj2 = manager.values("title", str_pk=Cast("pk", output_field=CharField()))[0]

        # Raw_values returns real database values regardless of current language
        assert raw_obj["title"] == raw_obj2["title"]
        assert raw_obj["str_pk"] == raw_obj2["str_pk"]
        # Values present language-aware data, from the moment of retrieval
        assert obj["title"] == "en"
        assert obj["str_pk"] == str(id1)
        assert obj2["title"] == "de"

        # Values_list behave similarly
        assert list(manager.values_list("title", Cast("pk", output_field=CharField()))) == [
            ("en", str(id1))
        ]
        with override("de"):
            assert list(manager.values_list("title", Cast("pk", output_field=CharField()))) == [
                ("de", str(id1))
            ]

    def test_custom_manager(self):
        """Test if user-defined manager is still working"""
        n = models.CustomManagerTestModel(title="")
        n.title_en = "enigma"
        n.title_de = "foo"
        n.save()

        m = models.CustomManagerTestModel(title="")
        m.title_en = "enigma"
        m.title_de = "bar"
        m.save()

        # Custom method
        assert "bar" == models.CustomManagerTestModel.objects.foo()

        # Ensure that get_queryset is working - filter objects to those with 'a' in title
        assert "en" == get_language()
        assert 2 == models.CustomManagerTestModel.objects.count()
        with override("de"):
            assert 1 == models.CustomManagerTestModel.objects.count()

    def test_custom_manager_custom_method_name(self):
        """Test if custom method also returns MultilingualQuerySet"""
        from modeltranslation.manager import MultilingualQuerySet

        qs = models.CustomManagerTestModel.objects.custom_qs()
        assert isinstance(qs, MultilingualQuerySet)

    def test_3rd_party_custom_manager(self):
        from django.contrib.auth.models import Group, GroupManager

        from modeltranslation.manager import MultilingualManager

        testmodel_fields = get_field_names(Group)
        assert "name" in testmodel_fields
        assert "name_de" in testmodel_fields
        assert "name_en" in testmodel_fields
        assert "name_en" in testmodel_fields

        assert isinstance(Group.objects, MultilingualManager)
        assert isinstance(Group.objects, GroupManager)
        assert "get_by_natural_key" in dir(Group.objects)

    def test_multilingual_queryset_pickling(self):
        import pickle

        from modeltranslation.manager import MultilingualQuerySet

        # typical
        models.CustomManagerTestModel.objects.create(title="a")
        qs = models.CustomManagerTestModel.objects.all()
        serialized = pickle.dumps(qs)
        deserialized = pickle.loads(serialized)
        assert isinstance(deserialized, MultilingualQuerySet)
        assert list(qs) == list(deserialized)

        # Generated class
        models.CustomManager2TestModel.objects.create()
        qs = models.CustomManager2TestModel.objects.all()
        serialized = pickle.dumps(qs)
        deserialized = pickle.loads(serialized)
        assert isinstance(deserialized, MultilingualQuerySet)
        assert isinstance(deserialized, models.CustomQuerySet)
        assert list(qs) == list(deserialized)

    def test_non_objects_manager(self):
        """Test if managers other than ``objects`` are patched too"""
        from modeltranslation.manager import MultilingualManager

        manager = models.CustomManagerTestModel.another_mgr_name
        assert isinstance(manager, MultilingualManager)

    def test_default_manager_for_inherited_models_with_custom_manager(self):
        """Test if default manager is still set from local managers"""
        manager = models.CustomManagerChildTestModel._meta.default_manager
        assert "objects" == manager.name
        assert isinstance(manager, MultilingualManager)
        assert isinstance(models.CustomManagerChildTestModel.translations, MultilingualManager)

    def test_default_manager_for_inherited_models(self):
        manager = models.PlainChildTestModel._meta.default_manager
        assert "objects" == manager.name
        assert isinstance(models.PlainChildTestModel.translations, MultilingualManager)

    def test_custom_manager2(self):
        """Test if user-defined queryset is still working"""
        from modeltranslation.manager import MultilingualManager, MultilingualQuerySet

        manager = models.CustomManager2TestModel.objects
        assert isinstance(manager, models.CustomManager2)
        assert isinstance(manager, MultilingualManager)
        qs = manager.all()
        assert isinstance(qs, models.CustomQuerySet)
        assert isinstance(qs, MultilingualQuerySet)

    def test_creation(self):
        """Test if field are rewritten in create."""
        assert "en" == get_language()
        n = models.ManagerTestModel.objects.create(title="foo")
        assert "foo" == n.title_en
        assert n.title_de is None
        assert "foo" == n.title

        # The same result
        n = models.ManagerTestModel.objects.create(title_en="foo")
        assert "foo" == n.title_en
        assert n.title_de is None
        assert "foo" == n.title

        # Language suffixed version wins
        n = models.ManagerTestModel.objects.create(title="bar", title_en="foo")
        assert "foo" == n.title_en
        assert n.title_de is None
        assert "foo" == n.title

    def test_creation_population(self):
        """Test if language fields are populated with default value on creation."""
        n = models.ManagerTestModel.objects.populate(True).create(title="foo")
        assert "foo" == n.title_en
        assert "foo" == n.title_de
        assert "foo" == n.title

        # You can specify some language...
        n = models.ManagerTestModel.objects.populate(True).create(title="foo", title_de="bar")
        assert "foo" == n.title_en
        assert "bar" == n.title_de
        assert "foo" == n.title

        # ... but remember that still original attribute points to current language
        assert "en" == get_language()
        n = models.ManagerTestModel.objects.populate(True).create(title="foo", title_en="bar")
        assert "bar" == n.title_en
        assert "foo" == n.title_de
        assert "bar" == n.title  # points to en
        with override("de"):
            assert "foo" == n.title  # points to de
        assert "en" == get_language()

        # This feature (for backward-compatibility) require populate method...
        n = models.ManagerTestModel.objects.create(title="foo")
        assert "foo" == n.title_en
        assert n.title_de is None
        assert "foo" == n.title

        # ... or MODELTRANSLATION_AUTO_POPULATE setting
        with reload_override_settings(MODELTRANSLATION_AUTO_POPULATE=True):
            assert mt_settings.AUTO_POPULATE is True
            n = models.ManagerTestModel.objects.create(title="foo")
            assert "foo" == n.title_en
            assert "foo" == n.title_de
            assert "foo" == n.title

            # populate method has highest priority
            n = models.ManagerTestModel.objects.populate(False).create(title="foo")
            assert "foo" == n.title_en
            assert n.title_de is None
            assert "foo" == n.title

        # Populate ``default`` fills just the default translation.
        # TODO: Having more languages would make these tests more meaningful.
        qs = models.ManagerTestModel.objects
        m = qs.populate("default").create(title="foo", description="bar")
        assert "foo" == m.title_de
        assert "foo" == m.title_en
        assert "bar" == m.description_de
        assert "bar" == m.description_en
        with override("de"):
            m = qs.populate("default").create(title="foo", description="bar")
            assert "foo" == m.title_de
            assert m.title_en is None
            assert "bar" == m.description_de
            assert m.description_en is None

        # Populate ``required`` fills just non-nullable default translations.
        qs = models.ManagerTestModel.objects
        m = qs.populate("required").create(title="foo", description="bar")
        assert "foo" == m.title_de
        assert "foo" == m.title_en
        assert m.description_de is None
        assert "bar" == m.description_en
        with override("de"):
            m = qs.populate("required").create(title="foo", description="bar")
            assert "foo" == m.title_de
            assert m.title_en is None
            assert "bar" == m.description_de
            assert m.description_en is None

    def test_get_or_create_population(self):
        """
        Populate may be used with ``get_or_create``.
        """
        qs = models.ManagerTestModel.objects
        m1, created1 = qs.populate(True).get_or_create(title="aaa")
        m2, created2 = qs.populate(True).get_or_create(title="aaa")
        assert created1
        assert not created2
        assert m1 == m2
        assert "aaa" == m1.title_en
        assert "aaa" == m1.title_de

    def test_fixture_population(self):
        """
        Test that a fixture with values only for the original fields
        does not result in missing default translations for (original)
        non-nullable fields.
        """
        with auto_populate("required"):
            call_command("loaddata", "fixture.json", verbosity=0)
            m = models.TestModel.objects.get()
            assert m.title_en == "foo"
            assert m.title_de == "foo"
            assert m.text_en == "bar"
            assert m.text_de is None

    def test_fixture_population_via_command(self):
        """
        Test that the loaddata command takes new option.
        """
        call_command("loaddata", "fixture.json", verbosity=0, populate="required")
        m = models.TestModel.objects.get()
        assert m.title_en == "foo"
        assert m.title_de == "foo"
        assert m.text_en == "bar"
        assert m.text_de is None

        call_command("loaddata", "fixture.json", verbosity=0, populate="all")
        m = models.TestModel.objects.get()
        assert m.title_en == "foo"
        assert m.title_de == "foo"
        assert m.text_en == "bar"
        assert m.text_de == "bar"

        # Test if option overrides current context
        with auto_populate("all"):
            call_command("loaddata", "fixture.json", verbosity=0, populate=False)
            m = models.TestModel.objects.get()
            assert m.title_en == "foo"
            assert m.title_de is None
            assert m.text_en == "bar"
            assert m.text_de is None

    def assertDeferred(self, use_defer, *fields):
        manager = models.TestModel.objects.defer if use_defer else models.TestModel.objects.only
        inst1 = manager(*fields)[0]
        with override("de"):
            inst2 = manager(*fields)[0]
        assert "title_en" == inst1.title
        assert "title_en" == inst2.title
        with override("de"):
            assert "title_de" == inst1.title
            assert "title_de" == inst2.title

    def assertDeferredClass(self, item):
        assert len(item.get_deferred_fields()) > 0

    def test_deferred(self):
        """
        Check if ``only`` and ``defer`` are working.
        """
        models.TestModel.objects.create(title_de="title_de", title_en="title_en")
        inst = models.TestModel.objects.only("title_en")[0]
        assert isinstance(inst, models.TestModel)
        self.assertDeferred(False, "title_en")

        with auto_populate("all"):
            self.assertDeferred(False, "title")
            self.assertDeferred(False, "title_de")
            self.assertDeferred(False, "title_en")
            self.assertDeferred(False, "title_en", "title_de")
            self.assertDeferred(False, "title", "title_en")
            self.assertDeferred(False, "title", "title_de")
            # Check if fields are deferred properly with ``only``
            self.assertDeferred(False, "text")

            # Defer
            self.assertDeferred(True, "title")
            self.assertDeferred(True, "title_de")
            self.assertDeferred(True, "title_en")
            self.assertDeferred(True, "title_en", "title_de")
            self.assertDeferred(True, "title", "title_en")
            self.assertDeferred(True, "title", "title_de")
            self.assertDeferred(True, "text", "email", "url")

    def test_deferred_fk(self):
        """
        Check if ``select_related`` is rewritten and also
        if ``only`` and ``defer`` are working with deferred classes
        """
        test = models.TestModel.objects.create(title_de="title_de", title_en="title_en")
        with auto_populate("all"):
            models.ForeignKeyModel.objects.create(test=test)

        item = models.ForeignKeyModel.objects.select_related("test").defer("test__text")[0]
        self.assertDeferredClass(item.test)
        assert "title_en" == item.test.title
        assert "title_en" == item.test.__class__.objects.only("title")[0].title
        with override("de"):
            item = models.ForeignKeyModel.objects.select_related("test").defer("test__text")[0]
            self.assertDeferredClass(item.test)
            assert "title_de" == item.test.title
            assert "title_de" == item.test.__class__.objects.only("title")[0].title

    def test_deferred_spanning(self):
        test = models.TestModel.objects.create(title_de="title_de", title_en="title_en")
        with auto_populate("all"):
            models.ForeignKeyModel.objects.create(test=test)

        item1 = models.ForeignKeyModel.objects.select_related("test").defer("test__text")[0].test
        item2 = models.TestModel.objects.defer("text")[0]
        assert item1.__class__ is item2.__class__
        # DeferredAttribute descriptors are present
        assert "text_en" in dir(item1.__class__)
        assert "text_de" in dir(item1.__class__)

    def test_deferred_rule2(self):
        models.TestModel.objects.create(title_de="title_de", title_en="title_en")
        o = models.TestModel.objects.only("title")[0]
        assert o.title == "title_en"
        o.title = "bla"
        assert o.title == "bla"

    def test_select_related(self):
        test = models.TestModel.objects.create(title_de="title_de", title_en="title_en")
        with auto_populate("all"):
            models.ForeignKeyModel.objects.create(untrans=test)

        fk_qs = models.ForeignKeyModel.objects.all()
        assert "untrans" not in fk_qs[0]._state.fields_cache
        assert "untrans" in fk_qs.select_related("untrans")[0]._state.fields_cache
        assert (
            "untrans"
            not in fk_qs.select_related("untrans").select_related(None)[0]._state.fields_cache
        )
        # untrans is nullable so not included when select_related=True
        assert "untrans" not in fk_qs.select_related()[0]._state.fields_cache

    def test_translation_fields_appending(self):
        from modeltranslation.manager import append_lookup_key, append_lookup_keys

        assert {"untrans"} == append_lookup_key(models.ForeignKeyModel, "untrans")
        assert {"title", "title_en", "title_de"} == append_lookup_key(
            models.ForeignKeyModel, "title"
        )
        assert {"test", "test_en", "test_de"} == append_lookup_key(models.ForeignKeyModel, "test")
        assert {"title__eq", "title_en__eq", "title_de__eq"} == append_lookup_key(
            models.ForeignKeyModel, "title__eq"
        )
        assert {"test__smt", "test_en__smt", "test_de__smt"} == append_lookup_key(
            models.ForeignKeyModel, "test__smt"
        )
        big_set = {
            "test__url",
            "test__url_en",
            "test__url_de",
            "test_en__url",
            "test_en__url_en",
            "test_en__url_de",
            "test_de__url",
            "test_de__url_en",
            "test_de__url_de",
        }
        assert big_set == append_lookup_key(models.ForeignKeyModel, "test__url")
        assert {"untrans__url", "untrans__url_en", "untrans__url_de"} == append_lookup_key(
            models.ForeignKeyModel, "untrans__url"
        )

        assert big_set.union(["title", "title_en", "title_de"]) == append_lookup_keys(
            models.ForeignKeyModel, ["test__url", "title"]
        )

    def test_constructor_inheritance(self):
        inst = models.AbstractModelB()
        # Check if fields assigned in constructor hasn't been ignored.
        assert inst.titlea == "title_a"
        assert inst.titleb == "title_b"

    def test_distinct(self):
        """Check that field names are rewritten in distinct keys."""
        manager = models.ManagerTestModel.objects
        manager.create(
            title_en="title_1_en",
            title_de="title_1_de",
            description_en="desc_1_en",
            description_de="desc_1_de",
        )
        manager.create(
            title_en="title_1_en",
            title_de="title_1_de",
            description_en="desc_2_en",
            description_de="desc_2_de",
        )
        manager.create(
            title_en="title_2_en",
            title_de="title_2_de",
            description_en="desc_1_en",
            description_de="desc_1_de",
        )
        manager.create(
            title_en="title_2_en",
            title_de="title_2_de",
            description_en="desc_2_en",
            description_de="desc_2_de",
        )

        # Without field arguments to distinct() all fields are used to determine
        # distinctness, therefore when only looking at a subset of fields in the
        # queryset it can appear that there are duplicates (the titles in this case)
        titles_for_en = tuple(m.title for m in manager.order_by("title").distinct())
        with override("de"):
            titles_for_de = tuple(m.title for m in manager.order_by("title").distinct())

        assert titles_for_en == ("title_1_en", "title_1_en", "title_2_en", "title_2_en")
        assert titles_for_de == ("title_1_de", "title_1_de", "title_2_de", "title_2_de")

        # On PostgreSQL only, distinct() can have field arguments (*fields) to specify which fields
        # the distinct applies to (this generates a DISTINCT ON (*fields) sql expression).
        # NB: DISTINCT ON expressions must be accompanied by an order_by() that starts with the
        # same fields in the same order
        if django_settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
            titles_for_en = tuple(
                (m.title, m.description)
                for m in manager.order_by("title", "description").distinct("title")
            )
            with override("de"):
                titles_for_de = tuple(
                    (m.title, m.description)
                    for m in manager.order_by("title", "description").distinct("title")
                )

            assert titles_for_en == (("title_1_en", "desc_1_en"), ("title_2_en", "desc_1_en"))
            assert titles_for_de == (("title_1_de", "desc_1_de"), ("title_2_de", "desc_1_de"))

    def test_annotate(self):
        """Test if annotating is language-aware."""
        test = models.TestModel.objects.create(title_en="title_en", title_de="title_de")

        assert "en" == get_language()
        assert (
            models.TestModel.objects.annotate(custom_title=F("title")).values_list(
                "custom_title", flat=True
            )[0]
            == "title_en"
        )
        with override("de"):
            assert (
                models.TestModel.objects.annotate(custom_title=F("title")).values_list(
                    "custom_title", flat=True
                )[0]
                == "title_de"
            )
            assert (
                models.TestModel.objects.annotate(
                    custom_title=Concat(F("title"), Value("value1"), Value("value2"))
                ).values_list("custom_title", flat=True)[0]
                == "title_devalue1value2"
            )
            assert (
                models.TestModel.objects.annotate(
                    custom_title=Concat(F("title"), Concat(F("title"), Value("value")))
                ).values_list("custom_title", flat=True)[0]
                == "title_detitle_devalue"
            )
        models.ForeignKeyModel.objects.create(test=test)
        models.ForeignKeyModel.objects.create(test=test)
        assert (
            models.TestModel.objects.annotate(Count("test_fks")).values_list(
                "test_fks__count", flat=True
            )[0]
            == 2
        )


class TranslationModelFormTest(ModeltranslationTestBase):
    def test_fields(self):
        class TestModelForm(TranslationModelForm):
            class Meta:
                model = models.TestModel
                fields = "__all__"

        form = TestModelForm()
        assert list(form.base_fields) == [
            "title",
            "title_de",
            "title_en",
            "text",
            "text_de",
            "text_en",
            "url",
            "url_de",
            "url_en",
            "email",
            "email_de",
            "email_en",
            "dynamic_default",
            "dynamic_default_de",
            "dynamic_default_en",
        ]
        assert list(form.fields) == ["title", "text", "url", "email", "dynamic_default"]

    def test_updating_with_empty_value(self):
        """
        Can we update the current language translation with an empty value, when
        the original field is excluded from the form?
        """

        class Form(forms.ModelForm):
            class Meta:
                model = models.TestModel
                exclude = ("text", "dynamic_default")

        instance = models.TestModel.objects.create(text_de="something")
        form = Form(
            {"text_de": "", "title": "a", "email_de": "", "email_en": ""}, instance=instance
        )
        instance = form.save()
        assert "de" == get_language()
        assert "" == instance.text_de


class ProxyModelTest(ModeltranslationTestBase):
    def test_equality(self):
        n = models.TestModel.objects.create(title="Title")
        m = models.ProxyTestModel.objects.get(title="Title")
        assert n.title == m.title
        assert n.title_de == m.title_de
        assert n.title_en == m.title_en


class TestRequired(ModeltranslationTestBase):
    def assertRequired(self, field_name):
        assert not self.opts.get_field(field_name).blank

    def assertNotRequired(self, field_name):
        assert self.opts.get_field(field_name).blank

    def test_required(self):
        self.opts = models.RequiredModel._meta

        # All non required
        self.assertNotRequired("non_req")
        self.assertNotRequired("non_req_en")
        self.assertNotRequired("non_req_de")

        # Original required, but translated fields not - default behaviour
        self.assertRequired("req")
        self.assertNotRequired("req_en")
        self.assertNotRequired("req_de")

        # Set all translated field required
        self.assertRequired("req_reg")
        self.assertRequired("req_reg_en")
        self.assertRequired("req_reg_de")

        # Set some translated field required
        self.assertRequired("req_en_reg")
        self.assertRequired("req_en_reg_en")
        self.assertNotRequired("req_en_reg_de")

        # Test validation
        inst = models.RequiredModel()
        inst.req = "abc"
        inst.req_reg = "def"
        try:
            inst.full_clean()
        except ValidationError as e:
            error_fields = set(e.message_dict.keys())
            assert {"req_reg_en", "req_en_reg", "req_en_reg_en"} == error_fields
        else:
            self.fail("ValidationError not raised!")


class M2MTest(ModeltranslationTestBase):
    def test_m2m(self):
        # Create 1 instance of Y, linked to 2 instance of X, with different
        # English and German names.
        x1 = models.ModelX.objects.create(name_en="foo", name_de="bar")
        x2 = models.ModelX.objects.create(name_en="bar", name_de="baz")
        y = models.ModelY.objects.create(title="y1")
        models.ModelXY.objects.create(model_x=x1, model_y=y)
        models.ModelXY.objects.create(model_x=x2, model_y=y)

        with override("en"):
            # There's 1 X named "foo" and it's x1
            y_foo = models.ModelY.objects.filter(xs__name="foo")
            assert 1 == y_foo.count()

            # There's 1 X named "bar" and it's x2 (in English)
            y_bar = models.ModelY.objects.filter(xs__name="bar")
            assert 1 == y_bar.count()

            # But in English, there's no X named "baz"
            y_baz = models.ModelY.objects.filter(xs__name="baz")
            assert 0 == y_baz.count()

            # Again: 1 X named "bar" (but through the M2M field)
            x_bar = y.xs.filter(name="bar")
            assert x2 in x_bar


class InheritedPermissionTestCase(ModeltranslationTestBase):
    def test_managers_failure(self):
        """This fails with 0.13b."""
        from django.contrib.auth.models import Permission, User

        from modeltranslation.manager import MultilingualManager

        from .models import InheritedPermission

        assert not isinstance(Permission.objects, MultilingualManager), (
            "Permission is using MultilingualManager"
        )
        assert isinstance(InheritedPermission.objects, MultilingualManager), (
            "InheritedPermission is not using MultilingualManager"
        )

        # This happens at initialization time, depending on the models
        # initialized.
        Permission._meta._expire_cache()

        assert not isinstance(Permission.objects, MultilingualManager), (
            "Permission is using MultilingualManager"
        )
        user = User.objects.create(username="123", is_active=True)
        user.has_perm("test_perm")
