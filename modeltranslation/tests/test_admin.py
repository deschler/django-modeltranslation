# pyright: reportGeneralTypeIssues=warning, reportOptionalMemberAccess=warning, reportOptionalOperand=warning

import pytest
from django import forms
from django.contrib.admin.sites import AdminSite
from django.db.models import TextField
from django.utils.translation import get_language, trans_real
from django.test import TestCase, RequestFactory

from modeltranslation import admin, translator
from modeltranslation.tests import models
from modeltranslation.utils import (
    build_css_class,
)

from .tests import reload_override_settings


class TranslationAdminTest(TestCase):
    def setUp(self):
        super().setUp()
        self.test_obj = models.TestModel.objects.create(title="Testtitle", text="Testtext")
        self.site = AdminSite()
        self.request = RequestFactory().get("/")

    def tearDown(self):
        self.test_obj.delete()
        super().tearDown()

    def test_default_fields(self):
        class TestModelAdmin(admin.TranslationAdmin):
            pass

        ma = TestModelAdmin(models.TestModel, self.site)
        assert tuple(ma.get_form(self.request).base_fields.keys()) == (
            "title_de",
            "title_en",
            "text_de",
            "text_en",
            "url_de",
            "url_en",
            "email_de",
            "email_en",
            "dynamic_default_de",
            "dynamic_default_en",
        )

    def test_model_with_constraint_fields(self):
        ma = admin.TranslationAdmin(models.ModelWithConstraint, self.site)

        assert tuple(ma.get_form(self.request).base_fields.keys()) == (
            "title",
            "sub_title_de",
            "sub_title_en",
        )

    def test_default_fieldsets(self):
        class TestModelAdmin(admin.TranslationAdmin):
            pass

        ma = TestModelAdmin(models.TestModel, self.site)
        # We expect that the original field is excluded and only the
        # translation fields are included in fields
        fields = [
            "title_de",
            "title_en",
            "text_de",
            "text_en",
            "url_de",
            "url_en",
            "email_de",
            "email_en",
            "dynamic_default_de",
            "dynamic_default_en",
        ]
        assert ma.get_fieldsets(self.request) == [(None, {"fields": fields})]
        assert ma.get_fieldsets(self.request, self.test_obj) == [(None, {"fields": fields})]

    def test_field_arguments(self):
        class TestModelAdmin(admin.TranslationAdmin):
            fields = ["title"]

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ["title_de", "title_en"]
        assert tuple(ma.get_form(self.request).base_fields.keys()) == tuple(fields)
        assert tuple(ma.get_form(self.request, self.test_obj).base_fields.keys()) == tuple(fields)

    def test_field_arguments_restricted_on_form(self):
        # Using `fields`.
        class TestModelAdmin(admin.TranslationAdmin):
            fields = ["title"]

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ["title_de", "title_en"]
        assert tuple(ma.get_form(self.request).base_fields.keys()) == tuple(fields)
        assert tuple(ma.get_form(self.request, self.test_obj).base_fields.keys()) == tuple(fields)

        # Using `fieldsets`.
        class TestModelAdmin(admin.TranslationAdmin):
            fieldsets = [(None, {"fields": ["title"]})]

        ma = TestModelAdmin(models.TestModel, self.site)
        assert tuple(ma.get_form(self.request).base_fields.keys()) == tuple(fields)
        assert tuple(ma.get_form(self.request, self.test_obj).base_fields.keys()) == tuple(fields)

        # Using `exclude`.
        class TestModelAdmin(admin.TranslationAdmin):
            exclude = ["url", "email", "dynamic_default"]

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ["title_de", "title_en", "text_de", "text_en"]
        assert tuple(ma.get_form(self.request).base_fields.keys()) == tuple(fields)

        # You can also pass a tuple to `exclude`.
        class TestModelAdmin(admin.TranslationAdmin):
            exclude = ("url", "email", "dynamic_default")

        ma = TestModelAdmin(models.TestModel, self.site)
        assert tuple(ma.get_form(self.request).base_fields.keys()) == tuple(fields)
        assert tuple(ma.get_form(self.request, self.test_obj).base_fields.keys()) == tuple(fields)

        # Using `fields` and `exclude`.
        class TestModelAdmin(admin.TranslationAdmin):
            fields = ["title", "url"]
            exclude = ["url"]

        ma = TestModelAdmin(models.TestModel, self.site)
        assert tuple(ma.get_form(self.request).base_fields.keys()) == ("title_de", "title_en")

        # Using `fields` and `readonly_fields`.
        class TestModelAdmin(admin.TranslationAdmin):
            fields = ["title", "url"]
            readonly_fields = ["url"]

        ma = TestModelAdmin(models.TestModel, self.site)
        assert tuple(ma.get_form(self.request).base_fields.keys()) == ("title_de", "title_en")

        # Using `readonly_fields`.
        # Note: readonly fields are not included in the form.
        class TestModelAdmin(admin.TranslationAdmin):
            readonly_fields = ["title"]

        ma = TestModelAdmin(models.TestModel, self.site)
        assert tuple(ma.get_form(self.request).base_fields.keys()) == (
            "text_de",
            "text_en",
            "url_de",
            "url_en",
            "email_de",
            "email_en",
            "dynamic_default_de",
            "dynamic_default_en",
        )

        # Using grouped fields.
        # Note: Current implementation flattens the nested fields.
        class TestModelAdmin(admin.TranslationAdmin):
            fields = (
                ("title", "url"),
                "email",
            )

        ma = TestModelAdmin(models.TestModel, self.site)
        assert tuple(ma.get_form(self.request).base_fields.keys()) == (
            "title_de",
            "title_en",
            "url_de",
            "url_en",
            "email_de",
            "email_en",
        )

        # Using grouped fields in `fieldsets`.
        class TestModelAdmin(admin.TranslationAdmin):
            fieldsets = [(None, {"fields": ("email", ("title", "url"))})]

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ["email_de", "email_en", "title_de", "title_en", "url_de", "url_en"]
        assert tuple(ma.get_form(self.request).base_fields.keys()) == tuple(fields)
        assert tuple(ma.get_form(self.request, self.test_obj).base_fields.keys()) == tuple(fields)

    def test_field_arguments_restricted_on_custom_form(self):
        # Using `fields`.
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = models.TestModel
                fields = ["url", "email"]

        class TestModelAdmin(admin.TranslationAdmin):
            form = TestModelForm

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ["url_de", "url_en", "email_de", "email_en"]
        assert tuple(ma.get_form(self.request).base_fields.keys()) == tuple(fields)
        assert tuple(ma.get_form(self.request, self.test_obj).base_fields.keys()) == tuple(fields)

        # Using `exclude`.
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = models.TestModel
                exclude = ["url", "email", "dynamic_default"]

        class TestModelAdmin(admin.TranslationAdmin):
            form = TestModelForm

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ["title_de", "title_en", "text_de", "text_en"]
        assert tuple(ma.get_form(self.request).base_fields.keys()) == tuple(fields)
        assert tuple(ma.get_form(self.request, self.test_obj).base_fields.keys()) == tuple(fields)

        # If both, the custom form an the ModelAdmin define an `exclude`
        # option, the ModelAdmin wins. This is Django behaviour.
        class TestModelAdmin(admin.TranslationAdmin):
            form = TestModelForm
            exclude = ["url", "dynamic_default"]

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ["title_de", "title_en", "text_de", "text_en", "email_de", "email_en"]
        assert tuple(ma.get_form(self.request).base_fields.keys()) == tuple(fields)
        assert tuple(ma.get_form(self.request, self.test_obj).base_fields.keys()) == tuple(fields)

        # Same for `fields`.
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = models.TestModel
                fields = ["text", "title"]

        class TestModelAdmin(admin.TranslationAdmin):
            form = TestModelForm
            fields = ["email"]

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ["email_de", "email_en"]
        assert tuple(ma.get_form(self.request).base_fields.keys()) == tuple(fields)
        assert tuple(ma.get_form(self.request, self.test_obj).base_fields.keys()) == tuple(fields)

    def test_model_form_widgets(self):
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = models.TestModel
                fields = [
                    "text",
                ]
                widgets = {
                    "text": forms.Textarea(attrs={"myprop": "myval"}),
                }

        class TestModelAdmin(admin.TranslationAdmin):
            form = TestModelForm

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ["text_de", "text_en"]
        assert tuple(ma.get_form(self.request).base_fields.keys()) == tuple(fields)
        assert tuple(ma.get_form(self.request, self.test_obj).base_fields.keys()) == tuple(fields)

        for field in fields:
            assert "myprop" in ma.get_form(self.request).base_fields.get(field).widget.attrs.keys()
            assert (
                "myval"
                in ma.get_form(self.request, self.test_obj)
                .base_fields.get(field)
                .widget.attrs.values()
            )

    def test_widget_ordering_via_formfield_for_dbfield(self):
        class TestModelAdmin(admin.TranslationAdmin):
            fields = ["text"]

            def formfield_for_dbfield(self, db_field, request, **kwargs):
                if isinstance(db_field, TextField):
                    kwargs["widget"] = forms.Textarea(attrs={"myprop": "myval"})
                    return db_field.formfield(**kwargs)
                return super().formfield_for_dbfield(db_field, self.request, **kwargs)

        ma = TestModelAdmin(models.TestModel, self.site)
        fields = ["text_de", "text_en"]
        assert tuple(ma.get_form(self.request).base_fields.keys()) == tuple(fields)
        assert tuple(ma.get_form(self.request, self.test_obj).base_fields.keys()) == tuple(fields)

        for field in fields:
            assert "myprop" in ma.get_form(self.request).base_fields.get(field).widget.attrs.keys()
            assert (
                "myval"
                in ma.get_form(self.request, self.test_obj)
                .base_fields.get(field)
                .widget.attrs.values()
            )

    def test_widget_classes_appended_by_formfield_for_dbfield(self):
        """
        Regression test for #660 (https://github.com/deschler/django-modeltranslation/issues/660)
        """

        class ForeignKeyModelModelAdmin(admin.TranslationAdmin):
            fields = ["test"]

        class OneToOneFieldModelAdmin(admin.TranslationAdmin):
            fields = ["test"]

        ma = ForeignKeyModelModelAdmin(models.ForeignKeyModel, self.site)
        fields = ["test_de", "test_en"]
        for field in fields:
            widget = ma.get_form(self.request).base_fields.get(field).widget
            # Django 5.1 Adds this attr, ignore it
            widget.attrs.pop("data-context", None)
            assert {} == widget.attrs
            assert "class" in widget.widget.attrs.keys()
            assert "mt" in widget.widget.attrs["class"]

    def test_inline_fieldsets(self):
        class DataInline(admin.TranslationStackedInline):
            model = models.DataModel
            fieldsets = [("Test", {"fields": ("data",)})]

        class TestModelAdmin(admin.TranslationAdmin):
            exclude = (
                "title",
                "text",
            )
            inlines = [DataInline]

        class DataTranslationOptions(translator.TranslationOptions):
            fields = ("data",)

        translator.translator.register(models.DataModel, DataTranslationOptions)
        ma = TestModelAdmin(models.TestModel, self.site)

        fieldsets = [("Test", {"fields": ["data_de", "data_en"]})]

        try:
            ma_fieldsets = ma.get_inline_instances(self.request)[0].get_fieldsets(self.request)
        except AttributeError:  # Django 1.3 fallback
            ma_fieldsets = ma.inlines[0](models.TestModel, self.site).get_fieldsets(self.request)
        assert ma_fieldsets == fieldsets

        try:
            ma_fieldsets = ma.get_inline_instances(self.request)[0].get_fieldsets(
                self.request, self.test_obj
            )
        except AttributeError:  # Django 1.3 fallback
            ma_fieldsets = ma.inlines[0](models.TestModel, self.site).get_fieldsets(
                self.request, self.test_obj
            )
        assert ma_fieldsets == fieldsets

        # Remove translation for DataModel
        translator.translator.unregister(models.DataModel)

    def test_list_editable(self):
        class TestModelAdmin(admin.TranslationAdmin):
            list_editable = ["title"]
            list_display = ["id", "title"]
            list_display_links = ["id"]

        ma = TestModelAdmin(models.TestModel, self.site)
        list_editable = ["title_de", "title_en"]
        list_display = ["id", "title_de", "title_en"]
        assert tuple(ma.list_editable) == tuple(list_editable)
        assert tuple(ma.list_display) == tuple(list_display)

    def test_build_css_class(self):
        with reload_override_settings(
            LANGUAGES=(
                ("de", "German"),
                ("en", "English"),
                ("es-ar", "Argentinian Spanish"),
            )
        ):
            fields = {
                "foo_en": "foo-en",
                "foo_es_ar": "foo-es_ar",
                "foo_en_us": "foo-en_us",
                "foo_bar_de": "foo_bar-de",
                "_foo_en": "_foo-en",
                "_foo_es_ar": "_foo-es_ar",
                "_foo_bar_de": "_foo_bar-de",
                "foo__en": "foo_-en",
                "foo__es_ar": "foo_-es_ar",
                "foo_bar__de": "foo_bar_-de",
            }
            for field, css in fields.items():
                assert build_css_class(field) == css

    def test_multitable_inheritance(self):
        class MultitableModelAAdmin(admin.TranslationAdmin):
            pass

        class MultitableModelBAdmin(admin.TranslationAdmin):
            pass

        maa = MultitableModelAAdmin(models.MultitableModelA, self.site)
        mab = MultitableModelBAdmin(models.MultitableModelB, self.site)

        assert tuple(maa.get_form(self.request).base_fields.keys()) == ("titlea_de", "titlea_en")
        assert tuple(mab.get_form(self.request).base_fields.keys()) == (
            "titlea_de",
            "titlea_en",
            "titleb_de",
            "titleb_en",
        )

    def test_group_fieldsets(self):
        # Declared fieldsets take precedence over group_fieldsets
        class GroupFieldsetsModelAdmin(admin.TranslationAdmin):
            fieldsets = [(None, {"fields": ["title"]})]
            group_fieldsets = True

        ma = GroupFieldsetsModelAdmin(models.GroupFieldsetsModel, self.site)
        fields = ["title_de", "title_en"]
        assert tuple(ma.get_form(self.request).base_fields.keys()) == tuple(fields)
        assert tuple(ma.get_form(self.request, self.test_obj).base_fields.keys()) == tuple(fields)

        # Now set group_fieldsets only
        class GroupFieldsetsModelAdmin(admin.TranslationAdmin):
            group_fieldsets = True

        ma = GroupFieldsetsModelAdmin(models.GroupFieldsetsModel, self.site)
        # Only text and title are registered for translation. We expect to get
        # three fieldsets. The first which gathers all untranslated field
        # (email only) and one for each translation field (text and title).
        fieldsets = [
            ("", {"fields": ["email"]}),
            ("Title", {"classes": ("mt-fieldset",), "fields": ["title_de", "title_en"]}),
            ("Text", {"classes": ("mt-fieldset",), "fields": ["text_de", "text_en"]}),
        ]
        assert ma.get_fieldsets(self.request) == fieldsets
        assert ma.get_fieldsets(self.request, self.test_obj) == fieldsets

        # Verify that other options are still taken into account

        # Exclude an untranslated field
        class GroupFieldsetsModelAdmin(admin.TranslationAdmin):
            group_fieldsets = True
            exclude = ("email",)

        ma = GroupFieldsetsModelAdmin(models.GroupFieldsetsModel, self.site)
        fieldsets = [
            ("Title", {"classes": ("mt-fieldset",), "fields": ["title_de", "title_en"]}),
            ("Text", {"classes": ("mt-fieldset",), "fields": ["text_de", "text_en"]}),
        ]
        assert ma.get_fieldsets(self.request) == fieldsets
        assert ma.get_fieldsets(self.request, self.test_obj) == fieldsets

        # Exclude a translation field
        class GroupFieldsetsModelAdmin(admin.TranslationAdmin):
            group_fieldsets = True
            exclude = ("text",)

        ma = GroupFieldsetsModelAdmin(models.GroupFieldsetsModel, self.site)
        fieldsets = [
            ("", {"fields": ["email"]}),
            ("Title", {"classes": ("mt-fieldset",), "fields": ["title_de", "title_en"]}),
        ]
        assert ma.get_fieldsets(self.request) == fieldsets
        assert ma.get_fieldsets(self.request, self.test_obj) == fieldsets

    def test_prepopulated_fields(self):
        trans_real.activate("de")
        assert get_language() == "de"

        # Non-translated slug based on translated field (using active language)
        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {"slug": ("firstname",)}

        ma = NameModelAdmin(models.NameModel, self.site)
        assert ma.prepopulated_fields == {"slug": ("firstname_de",)}

        # Checking multi-field
        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {
                "slug": (
                    "firstname",
                    "lastname",
                )
            }

        ma = NameModelAdmin(models.NameModel, self.site)
        assert ma.prepopulated_fields == {
            "slug": (
                "firstname_de",
                "lastname_de",
            )
        }

        # Non-translated slug based on non-translated field (no change)
        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {"slug": ("age",)}

        ma = NameModelAdmin(models.NameModel, self.site)
        assert ma.prepopulated_fields == {"slug": ("age",)}

        # Translated slug based on non-translated field (all populated on the same value)
        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {"slug2": ("age",)}

        ma = NameModelAdmin(models.NameModel, self.site)
        assert ma.prepopulated_fields == {"slug2_en": ("age",), "slug2_de": ("age",)}

        # Translated slug based on translated field (corresponding)
        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {"slug2": ("firstname",)}

        ma = NameModelAdmin(models.NameModel, self.site)
        assert ma.prepopulated_fields == {
            "slug2_en": ("firstname_en",),
            "slug2_de": ("firstname_de",),
        }

        # Check that current active language is used
        trans_real.activate("en")
        assert get_language() == "en"

        class NameModelAdmin(admin.TranslationAdmin):
            prepopulated_fields = {"slug": ("firstname",)}

        ma = NameModelAdmin(models.NameModel, self.site)
        assert ma.prepopulated_fields == {"slug": ("firstname_en",)}

        # Prepopulation language can be overriden by MODELTRANSLATION_PREPOPULATE_LANGUAGE
        with reload_override_settings(MODELTRANSLATION_PREPOPULATE_LANGUAGE="de"):

            class NameModelAdmin(admin.TranslationAdmin):
                prepopulated_fields = {"slug": ("firstname",)}

            ma = NameModelAdmin(models.NameModel, self.site)
            assert ma.prepopulated_fields == {"slug": ("firstname_de",)}

    def test_proxymodel_field_argument(self):
        class ProxyTestModelAdmin(admin.TranslationAdmin):
            fields = ["title"]

        ma = ProxyTestModelAdmin(models.ProxyTestModel, self.site)
        fields = ["title_de", "title_en"]
        assert tuple(ma.get_form(self.request).base_fields.keys()) == tuple(fields)
        assert tuple(ma.get_form(self.request, self.test_obj).base_fields.keys()) == tuple(fields)

    def test_class_attribute_access_raises_type_error(self):
        # Test for django-cms compatibility
        # https://github.com/django-cms/django-cms/issues/7948
        class TestModelAdmin(admin.TranslationAdmin[models.TestModel]):
            allow_children = True

        with pytest.raises(KeyError):
            TestModelAdmin["allow_children"]
