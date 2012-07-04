# -*- coding: utf-8 -*-
from copy import deepcopy

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.contrib import admin
from django.contrib.admin.options import BaseModelAdmin, InlineModelAdmin
from django.contrib.contenttypes import generic
from django import forms

from modeltranslation.settings import DEFAULT_LANGUAGE
from modeltranslation.translator import translator
from modeltranslation.utils import (get_translation_fields,
                                    build_localized_fieldname)
# Ensure that models are registered for translation before TranslationAdmin
# runs. The import is supposed to resolve a race condition between model import
# and translation registration in production (see issue 19).
import modeltranslation.models


class TranslationBaseModelAdmin(BaseModelAdmin):
    _orig_was_required = {}
    exclude_languages = []

    def __init__(self, *args, **kwargs):
        super(TranslationBaseModelAdmin, self).__init__(*args, **kwargs)
        self.trans_opts = translator.get_options_for_model(self.model)
        # TODO: Handle fields and exclude in form option.
        if hasattr(self.form, '_meta') and (getattr(self.form._meta, 'fields')
            or getattr(self.form._meta, 'exclude')):
            raise ImproperlyConfigured(
                'The options fields and exclude in a custom ModelForm are '
                'currently not supported by modeltranslation.')

    def _declared_fieldsets(self):
        if self.fieldsets:
            return self._patch_fieldsets(self.fieldsets)
        elif self.fields:
            return [
                (None, {'fields': self.replace_orig_field(self.fields)})]
        return None
    declared_fieldsets = property(_declared_fieldsets)

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super(TranslationBaseModelAdmin, self).formfield_for_dbfield(
            db_field, **kwargs)
        self.patch_translation_field(db_field, field, **kwargs)
        return field

    def patch_translation_field(self, db_field, field, **kwargs):
        trans_opts = translator.get_options_for_model(self.model)

        if db_field.name in trans_opts.fields:
            if field.required:
                field.required = False
                field.blank = True
                self._orig_was_required[
                    '%s.%s' % (db_field.model._meta, db_field.name)] = True

        # For every localized field copy the widget from the original field
        # and add a css class to identify a modeltranslation widget.
        if db_field.name in trans_opts.localized_fieldnames_rev:
            orig_fieldname = trans_opts.localized_fieldnames_rev[db_field.name]
            orig_formfield = self.formfield_for_dbfield(
                self.model._meta.get_field(orig_fieldname), **kwargs)
            field.widget = deepcopy(orig_formfield.widget)
            css_classes = field.widget.attrs.get('class', '').split(' ')
            css_classes.append('modeltranslation')

            if db_field.language == DEFAULT_LANGUAGE:
                # Add another css class to identify a default modeltranslation
                # widget.
                css_classes.append('modeltranslation-default')
                if (orig_formfield.required or
                    self._orig_was_required.get(
                        '%s.%s' % (db_field.model._meta, orig_fieldname))):
                    # In case the original form field was required, make the
                    # default translation field required instead.
                    orig_formfield.required = False
                    orig_formfield.blank = True
                    field.required = True
                    field.blank = False
            field.widget.attrs['class'] = ' '.join(css_classes)

    def _exclude_original_fields(self, exclude=None):
        if exclude is None:
            exclude = tuple()
        if exclude:
            exclude_new = tuple(exclude)
            return exclude_new + tuple(self.trans_opts.fields)
        return tuple(self.trans_opts.fields)

    def replace_orig_field(self, option):
        """
        Replaces each original field in `option` that is registered for
        translation by its translation fields.

        Returns a new list with replaced fields. If `option` contains no
        registered fields, it is returned unmodified.

        >>> print self.trans_opts.fields
        ('title',)
        >>> get_translation_fields(self.trans_opts.fields[0])
        ['title_de', 'title_en']
        >>> self.replace_orig_field(['title', 'url'])
        ['title_de', 'title_en', 'url']
        """
        # TODO: Handle nested lists to display multiple fields on same line.
        if option:
            option_new = list(option)
            for opt in option:
                if opt in self.trans_opts.fields:
                    index = option_new.index(opt)
                    translation_fields = get_translation_fields(opt)
                    option_new[index:index + 1] = translation_fields
            option = option_new
        return option

    def _patch_fieldsets(self, fieldsets, exclude_languages=None):
        # TODO: Handle nested lists to display multiple fields on same line.
        if exclude_languages is None:
            exclude_languages = []
        if fieldsets:
            fieldsets_new = list(fieldsets)
            for (name, dct) in fieldsets:
                if 'fields' in dct:
                    fields = self.replace_orig_field(dct['fields'])
                    excludes = self.get_translation_field_excludes(
                        exclude_languages)
                    dct['fields'] = [f for f in fields if f not in excludes]
                    #dct['fields'] = self.replace_orig_field(dct['fields'])
            fieldsets = fieldsets_new
        return fieldsets

    def get_translation_field_excludes(self, exclude_languages=None):
        """
        Returns a tuple of translation field names to exclude.

        Defaults to ``self.exclude_languages`` in case ``exclude_languages``
        parameter isn't set.
        """
        if exclude_languages is None:
            exclude_languages = []
        if exclude_languages:
            excl_languages = exclude_languages
        else:
            for lang in self.exclude_languages:
                # TODO: Not a good place for validation.
                if lang not in [l[0] for l in settings.LANGUAGES]:
                    raise ImproperlyConfigured(
                        'Language %s not in LANGUAGES setting.' % lang)
            excl_languages = self.exclude_languages
        exclude = []
        for orig_fieldname, translation_fields in \
            self.trans_opts.localized_fieldnames.iteritems():
            for tfield in translation_fields:
                language = tfield.split('_')[-1]
                if (language in excl_languages
                    and tfield not in exclude):
                    exclude.append(tfield)
        return tuple(exclude)

    def _do_get_form_or_formset(self, **kwargs):
        """
        Code shared among get_form and get_formset.
        """
        exclude = kwargs.get('exclude', [])
        exclude_languages = kwargs.get('exclude_languages', [])
        # self.exclude_languages = exclude_languages
        self.exclude = self.replace_orig_field(self.exclude)
        self.fieldsets = self._patch_fieldsets(
            self.fieldsets, exclude_languages)
        exclude_fields = (
            self.get_translation_field_excludes(self.exclude_languages) +
            self._exclude_original_fields(exclude))
        if self.exclude:
            exclude_fields = tuple(self.exclude) + tuple(exclude_fields)
        if exclude_fields:
            kwargs.update({'exclude': getattr(
                kwargs, 'exclude', tuple()) + exclude_fields})
        if kwargs.get('exclude_languages'):
            del kwargs['exclude_languages']
        return kwargs

    def _do_get_fieldsets_pre_form_or_formset(self, exclude_languages=None):
        """
        Common get_fieldsets code shared among TranslationAdmin and
        TranslationInlineModelAdmin.
        """
        if exclude_languages is None:
            exclude_languages = []
        fields = self.replace_orig_field(self._declared_fieldsets())
        excludes = self.get_translation_field_excludes(
            exclude_languages)
        filtered_fields = [f for f in fields if f not in excludes]
        return filtered_fields

    def _do_get_fieldsets_post_form_or_formset(self, request, form, obj=None,
                                               exclude_languages=None):
        """
        Common get_fieldsets code shared among TranslationAdmin and
        TranslationInlineModelAdmin.
        """
        if exclude_languages is None:
            exclude_languages = []
        base_fields = self.replace_orig_field(form.base_fields.keys())
        excludes = self.get_translation_field_excludes(
            exclude_languages)
        filtered_fields = [f for f in base_fields if f not in excludes]
        fields = filtered_fields + list(
            self.get_readonly_fields(request, obj))
        return [(None, {'fields': self.replace_orig_field(fields)})]


class TranslationAdmin(TranslationBaseModelAdmin, admin.ModelAdmin):
    def __init__(self, *args, **kwargs):
        super(TranslationAdmin, self).__init__(*args, **kwargs)
        self._patch_list_editable()
        self._patch_prepopulated_fields()

    def _patch_list_editable(self):
        if self.list_editable:
            editable_new = list(self.list_editable)
            display_new = list(self.list_display)
            for field in self.list_editable:
                if field in self.trans_opts.fields:
                    index = editable_new.index(field)
                    display_index = display_new.index(field)
                    translation_fields = get_translation_fields(field)
                    editable_new[index:index + 1] = translation_fields
                    display_new[display_index:display_index + 1] = \
                        translation_fields
            self.list_editable = editable_new
            self.list_display = display_new

    def _patch_prepopulated_fields(self):
        if self.prepopulated_fields:
            prepopulated_fields_new = dict(self.prepopulated_fields)
            for (k, v) in self.prepopulated_fields.items():
                if v[0] in self.trans_opts.fields:
                    translation_fields = get_translation_fields(v[0])
                    prepopulated_fields_new[k] = tuple([translation_fields[0]])
            self.prepopulated_fields = prepopulated_fields_new

    def get_form(self, request, obj=None, **kwargs):
        kwargs = self._do_get_form_or_formset(**kwargs)
        return super(TranslationAdmin, self).get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None, exclude_languages=None):
        if exclude_languages is None:
            exclude_languages = []
#        if self.declared_fieldsets:
#            fields = self.replace_orig_field(self._declared_fieldsets())
#            excludes = self.get_translation_field_excludes(
#                exclude_languages)
#            filtered_fields = [f for f in fields if f not in excludes]
#            return filtered_fields
#        form = self.get_form(request, obj)
#        base_fields = self.replace_orig_field(form.base_fields.keys())
#        excludes = self.get_translation_field_excludes(
#            exclude_languages)
#        filtered_fields = [f for f in base_fields if f not in excludes]
#        fields = filtered_fields + list(
#            self.get_readonly_fields(request, obj))
#        return [(None, {'fields': self.replace_orig_field(fields)})]
        if self.declared_fieldsets:
            return self._do_get_fieldsets_pre_form_or_formset(
                exclude_languages)
        form = self.get_form(request, obj)
        return self._do_get_fieldsets_post_form_or_formset(
            request, form, obj, exclude_languages)

    def save_model(self, request, obj, form, change):
        # Rule is: 3. Assigning a value to a translation field of the default
        # language also updates the original field.
        # Ensure that an empty default language field value clears the default
        # field. See issue 47 for details.
        trans_opts = translator.get_options_for_model(self.model)
        for k, v in trans_opts.localized_fieldnames.items():
            if getattr(obj, k):
                default_lang_fieldname = build_localized_fieldname(
                    k, DEFAULT_LANGUAGE)
                if not getattr(obj, default_lang_fieldname):
                    # TODO: Handle null values
                    setattr(obj, k, "")
        super(TranslationAdmin, self).save_model(request, obj, form, change)


class TranslationInlineModelAdmin(TranslationBaseModelAdmin, InlineModelAdmin):
    def get_formset(self, request, obj=None, **kwargs):
        kwargs = self._do_get_form_or_formset(**kwargs)
        return super(TranslationInlineModelAdmin, self).get_formset(
            request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None, exclude_languages=None):
        if exclude_languages is None:
            exclude_languages = []
        if self.declared_fieldsets:
            return self._do_get_fieldsets_pre_form_or_formset(
                exclude_languages)
        form = self.get_formset(request, obj).form
        return self._do_get_fieldsets_post_form_or_formset(
            request, form, obj, exclude_languages)


class TranslationTabularInline(TranslationInlineModelAdmin,
                               admin.TabularInline):
    pass


class TranslationStackedInline(TranslationInlineModelAdmin,
                               admin.StackedInline):
    pass


class TranslationGenericTabularInline(TranslationInlineModelAdmin,
                                      generic.GenericTabularInline):
    pass


class TranslationGenericStackedInline(TranslationInlineModelAdmin,
                                      generic.GenericStackedInline):
    pass
