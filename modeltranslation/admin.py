from __future__ import annotations
from pprint import pprint, pformat
from copy import deepcopy
from typing import Any, TypeVar, TYPE_CHECKING
from collections.abc import Iterable, Sequence

from django import forms
from django.db.models import Field, Model
from django.contrib import admin
from django.contrib.admin.options import BaseModelAdmin, InlineModelAdmin, flatten_fieldsets
from django.contrib.contenttypes.admin import GenericStackedInline, GenericTabularInline
from django.forms.models import BaseInlineFormSet
from django.http.request import HttpRequest

from modeltranslation import settings as mt_settings
from modeltranslation.translator import translator
from modeltranslation.utils import (
    build_css_class,
    build_localized_fieldname,
    get_language,
    get_language_bidi,
    get_translation_fields,
    unique,
)
from modeltranslation.widgets import ClearableWidgetWrapper
from modeltranslation._typing import _ListOrTuple

if TYPE_CHECKING:
    # We depend here or `django-stubs` internal `_FieldsetSpec`,
    # in case it changes, change import or define this internally.
    from django.contrib.admin.options import _FieldsetSpec

_ModelT = TypeVar("_ModelT", bound=Model)


class TranslationBaseModelAdmin(BaseModelAdmin[_ModelT]):
    _orig_was_required: dict[str, bool] = {}
    both_empty_values_fields = ()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.trans_opts = translator.get_options_for_model(self.model)
        self._patch_prepopulated_fields()

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        return self._patch_fieldsets(fieldsets)

    def __get_declared_fieldsets(
        self, request: HttpRequest, obj: _ModelT | None = None
    ) -> _FieldsetSpec | None:
        # Take custom modelform fields option into account
        if not self.fields and hasattr(self.form, "_meta") and self.form._meta.fields:
            self.fields = self.form._meta.fields  # type: ignore[assignment]
        # takes into account non-standard add_fieldsets attribute used by UserAdmin
        fieldsets = (
            self.add_fieldsets
            if getattr(self, "add_fieldsets", None) and obj is None
            else self.fieldsets
        )
        if fieldsets:
            return self._patch_fieldsets(fieldsets)
        elif self.fields:
            return [(None, {"fields": self.replace_orig_field(self.get_fields(request, obj))})]
        return None

    def _patch_fieldsets(self, fieldsets: _FieldsetSpec) -> _FieldsetSpec:
        fieldsets_new = list(fieldsets)
        for name, dct in fieldsets:
            if "fields" in dct:
                dct["fields"] = self.replace_orig_field(dct["fields"], preserve_originals=True)
        pprint(fieldsets_new)
        return fieldsets_new

    def formfield_for_dbfield(
        self, db_field: Field, request: HttpRequest, **kwargs: Any
    ) -> forms.Field | None:
        if field := super().formfield_for_dbfield(db_field, request, **kwargs):
            self.patch_translation_field(db_field, field, request, **kwargs)
        return field

    def patch_translation_field(
        self, db_field: Field, field: forms.Field, request: HttpRequest, **kwargs: Any
    ) -> None:
        if db_field.name in self.trans_opts.all_fields:
            if field.required:
                field.required = False
                field.blank = True
                self._orig_was_required["%s.%s" % (db_field.model._meta, db_field.name)] = True

        # For every localized field copy the widget from the original field
        # and add a css class to identify a modeltranslation widget.
        try:
            orig_field = db_field.translated_field
        except AttributeError:
            pass
        else:
            orig_formfield = self.formfield_for_dbfield(orig_field, request, **kwargs)
            if orig_formfield is None:
                return
            field.widget = deepcopy(orig_formfield.widget)
            attrs = field.widget.attrs
            # if any widget attrs are defined on the form they should be copied
            try:
                # this is a class:
                field.widget = deepcopy(self.form._meta.widgets[orig_field.name])  # type: ignore[index]
                if isinstance(field.widget, type):  # if not initialized
                    field.widget = field.widget(attrs)  # initialize form widget with attrs
            except (AttributeError, TypeError, KeyError):
                pass
            # field.widget = deepcopy(orig_formfield.widget)
            if orig_field.name in self.both_empty_values_fields:
                from modeltranslation.forms import NullableField, NullCharField

                form_class = field.__class__
                if issubclass(form_class, NullCharField):
                    # NullableField don't work with NullCharField
                    form_class.__bases__ = tuple(
                        b for b in form_class.__bases__ if b != NullCharField
                    )
                field.__class__ = type(
                    "Nullable%s" % form_class.__name__, (NullableField, form_class), {}
                )
            if (
                db_field.empty_value == "both" or orig_field.name in self.both_empty_values_fields
            ) and isinstance(field.widget, (forms.TextInput, forms.Textarea)):
                field.widget = ClearableWidgetWrapper(field.widget)
            css_classes = self._get_widget_from_field(field).attrs.get("class", "").split(" ")
            css_classes.append("mt")
            # Add localized fieldname css class
            css_classes.append(build_css_class(db_field.name, "mt-field"))
            # Add mt-bidi css class if language is bidirectional
            if get_language_bidi(db_field.language):
                css_classes.append("mt-bidi")
            if db_field.language == mt_settings.DEFAULT_LANGUAGE:
                # Add another css class to identify a default modeltranslation widget
                css_classes.append("mt-default")
                if orig_formfield.required or self._orig_was_required.get(
                    "%s.%s" % (orig_field.model._meta, orig_field.name)
                ):
                    # In case the original form field was required, make the
                    # default translation field required instead.
                    orig_formfield.required = False
                    orig_formfield.blank = True
                    field.required = True
                    field.blank = False
                    # Hide clearable widget for required fields
                    if isinstance(field.widget, ClearableWidgetWrapper):
                        field.widget = field.widget.widget
            self._get_widget_from_field(field).attrs["class"] = " ".join(css_classes)

    def _get_widget_from_field(self, field: forms.Field) -> Any:
        # retrieve "nested" widget in case of related field
        if isinstance(field.widget, admin.widgets.RelatedFieldWidgetWrapper):
            return field.widget.widget
        else:
            return field.widget

    def replace_orig_field(self, option: Iterable[str | Sequence[str]], preserve_originals = False) -> _ListOrTuple[str]:
        """
        Replaces each original field in `option` that is registered for
        translation by its translation fields.

        Returns a new list with replaced fields. If `option` contains no
        registered fields, it is returned unmodified.

        >>> self = TranslationAdmin()  # PyFlakes
        >>> print(self.trans_opts.fields.keys())
        ['title',]
        >>> get_translation_fields(self.trans_opts.fields.keys()[0])
        ['title_de', 'title_en']
        >>> self.replace_orig_field(['title', 'url'])
        ['title_de', 'title_en', 'url']

        Note that grouped fields are flattened. We do this because:

            1. They are hard to handle in the jquery-ui tabs implementation
            2. They don't scale well with more than a few languages
            3. It's better than not handling them at all (okay that's weak)

        >>> self.replace_orig_field((('title', 'url'), 'email', 'text'))
        ['title_de', 'title_en', 'url_de', 'url_en', 'email_de', 'email_en', 'text']
        """
        if option:
            option_new = list(option)

            def insert_at(opt):
                index = option_new.index(opt)
                where = 1 if preserve_originals else 0
                return slice(index + where, index + 1)

            for opt in option:
                if opt in self.trans_opts.all_fields:
                    translated_field_names = get_translation_fields(opt)
                    if any(name for name in translated_field_names if name in option):
                        # This set is already processed
                        return option
                    option_new[insert_at(opt)] = translated_field_names  # type: ignore[arg-type]
                elif isinstance(opt, (tuple, list)) and (
                    [o for o in opt if o in self.trans_opts.all_fields]
                ):
                    option_new[insert_at(opt)] = self.replace_orig_field(opt)
            option = option_new
        return option  # type: ignore[return-value]

    def _patch_prepopulated_fields(self) -> None:
        def localize(sources: Sequence[str], lang: str) -> tuple[str, ...]:
            "Append lang suffix (if applicable) to field list"

            def append_lang(source: str) -> str:
                if source in self.trans_opts.all_fields:
                    return build_localized_fieldname(source, lang)
                return source

            return tuple(map(append_lang, sources))

        prepopulated_fields: dict[str, Sequence[str]] = {}
        for dest, sources in self.prepopulated_fields.items():
            if dest in self.trans_opts.all_fields:
                for lang in mt_settings.AVAILABLE_LANGUAGES:
                    key = build_localized_fieldname(dest, lang)
                    prepopulated_fields[key] = localize(sources, lang)
            else:
                lang = mt_settings.PREPOPULATE_LANGUAGE or get_language()
                prepopulated_fields[dest] = localize(sources, lang)
        self.prepopulated_fields = prepopulated_fields

    def _get_form_or_formset(
        self, request: HttpRequest, obj: Model | None, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Generic code shared by get_form and get_formset.
        """
        exclude = self.get_exclude(request, obj)  # type: ignore[arg-type]
        if exclude is None:
            exclude = []
        else:
            exclude = list(exclude)
        exclude.extend(self.get_readonly_fields(request, obj))  # type: ignore[arg-type]
        if not exclude and hasattr(self.form, "_meta") and self.form._meta.exclude:
            # Take the custom ModelForm's Meta.exclude into account only if the
            # ModelAdmin doesn't define its own.
            exclude.extend(self.form._meta.exclude)

        # FIXME: idea
        # We need to somehow exclude original fields, but preserve them for validation
        # Make them readonly via widgets? Hidden via widgets?

        exclude = self.replace_orig_field(exclude)
        #exclude = self._exclude_original_fields(exclude)
        kwargs.update({
            "exclude": exclude or None,
            "widgets": {field_name: forms.HiddenInput() for field_name in self.trans_opts.all_fields.keys()} or None,
        })
        print("_get_form_or_formset->kwargs:", pformat(kwargs))

        return kwargs

    def _exclude_original_fields(self, exclude: _ListOrTuple[str]) -> tuple[str, ...]:
        return (
            *exclude,
            *self.trans_opts.all_fields.keys(),
        )

    def get_readonly_fields(
        self, request: HttpRequest, obj: _ModelT | None = None
    ) -> _ListOrTuple[str]:
        """
        Hook to specify custom readonly fields.
        """
        return self.replace_orig_field(self.readonly_fields)


class TranslationAdmin(TranslationBaseModelAdmin[_ModelT], admin.ModelAdmin[_ModelT]):
    # TODO: Consider addition of a setting which allows to override the fallback to True
    group_fieldsets = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._patch_list_editable()

    def _patch_list_editable(self) -> None:
        if self.list_editable:
            editable_new = list(self.list_editable)
            display_new = list(self.list_display)
            for field in self.list_editable:
                if field in self.trans_opts.all_fields:
                    index = editable_new.index(field)
                    display_index = display_new.index(field)
                    translation_fields = get_translation_fields(field)
                    editable_new[index : index + 1] = translation_fields
                    display_new[display_index : display_index + 1] = translation_fields
            self.list_editable = editable_new
            self.list_display = display_new

    def _group_fieldsets(self, fieldsets: list) -> list:
        # Fieldsets are not grouped by default. The function is activated by
        # setting TranslationAdmin.group_fieldsets to True. If the admin class
        # already defines a fieldset, we leave it alone and assume the author
        # has done whatever grouping for translated fields they desire.
        if self.group_fieldsets is True:
            flattened_fieldsets = flatten_fieldsets(fieldsets)

            # Create a fieldset to group each translated field's localized fields
            fields = sorted(f for f in self.opts.get_fields() if f.concrete)  # type: ignore[type-var]
            untranslated_fields = [
                f.name
                for f in fields
                if (
                    # Exclude the primary key field
                    f is not self.opts.auto_field
                    # Exclude non-editable fields
                    and f.editable
                    # Exclude the translation fields
                    and not hasattr(f, "translated_field")
                    # Honour field arguments. We rely on the fact that the
                    # passed fieldsets argument is already fully filtered
                    # and takes options like exclude into account.
                    and f.name in flattened_fieldsets
                )
            ]
            # TODO: Allow setting a label
            fieldsets = (
                [
                    (
                        "",
                        {"fields": untranslated_fields},
                    )
                ]
                if untranslated_fields
                else []
            )

            temp_fieldsets = {}
            for orig_field, trans_fields in self.trans_opts.all_fields.items():
                trans_fieldnames = [f.name for f in sorted(trans_fields, key=lambda x: x.name)]
                if any(f in trans_fieldnames for f in flattened_fieldsets):
                    # Extract the original field's verbose_name for use as this
                    # fieldset's label - using gettext_lazy in your model
                    # declaration can make that translatable.
                    label = self.model._meta.get_field(orig_field).verbose_name.capitalize()  # type: ignore[union-attr]
                    temp_fieldsets[orig_field] = (
                        label,
                        {"fields": trans_fieldnames, "classes": ("mt-fieldset",)},
                    )

            fields_order = unique(
                f.translated_field.name
                for f in self.opts.fields
                if hasattr(f, "translated_field") and f.name in flattened_fieldsets
            )
            for field_name in fields_order:
                fieldsets.append(temp_fieldsets.pop(field_name))
            assert not temp_fieldsets  # cleaned

        return fieldsets

    def get_form(
        self, request: HttpRequest, obj: _ModelT | None = None, **kwargs: Any
    ) -> type[forms.ModelForm]:
        kwargs = self._get_form_or_formset(request, obj, **kwargs)
        return super().get_form(request, obj, **kwargs)


_ChildModelT = TypeVar("_ChildModelT", bound=Model)
_ParentModelT = TypeVar("_ParentModelT", bound=Model)


class TranslationInlineModelAdmin(
    TranslationBaseModelAdmin[_ChildModelT], InlineModelAdmin[_ChildModelT, _ParentModelT]
):
    def get_formset(
        self, request: HttpRequest, obj: _ParentModelT | None = None, **kwargs: Any
    ) -> type[BaseInlineFormSet]:
        kwargs = self._get_form_or_formset(request, obj, **kwargs)
        return super().get_formset(request, obj, **kwargs)


class TranslationTabularInline(
    TranslationInlineModelAdmin[_ChildModelT, _ParentModelT],
    admin.TabularInline[_ChildModelT, _ParentModelT],
):
    pass


class TranslationStackedInline(
    TranslationInlineModelAdmin[_ChildModelT, _ParentModelT],
    admin.StackedInline[_ChildModelT, _ParentModelT],
):
    pass


class TranslationGenericTabularInline(
    TranslationInlineModelAdmin[_ChildModelT, _ParentModelT], GenericTabularInline
):
    pass


class TranslationGenericStackedInline(
    TranslationInlineModelAdmin[_ChildModelT, _ParentModelT], GenericStackedInline
):
    pass


class TabbedDjangoJqueryTranslationAdmin(TranslationAdmin[_ModelT]):
    """
    Convenience class which includes the necessary media files for tabbed
    translation fields. Reuses Django's internal jquery version.
    """

    class Media:
        js = (
            "admin/js/jquery.init.js",
            "modeltranslation/js/force_jquery.js",
            mt_settings.JQUERY_UI_URL,
            "modeltranslation/js/tabbed_translation_fields.js",
        )
        css = {
            "all": ("modeltranslation/css/tabbed_translation_fields.css",),
        }


class TabbedExternalJqueryTranslationAdmin(TranslationAdmin[_ModelT]):
    """
    Convenience class which includes the necessary media files for tabbed
    translation fields. Loads recent jquery version from a cdn.
    """

    class Media:
        js = (
            mt_settings.JQUERY_URL,
            mt_settings.JQUERY_UI_URL,
            "modeltranslation/js/tabbed_translation_fields.js",
        )
        css = {
            "screen": ("modeltranslation/css/tabbed_translation_fields.css",),
        }


TabbedTranslationAdmin = TabbedDjangoJqueryTranslationAdmin
