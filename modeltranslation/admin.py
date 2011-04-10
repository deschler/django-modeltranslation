# -*- coding: utf-8 -*-
from copy import copy

from django import forms, template
from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes import generic

from modeltranslation.settings import *
from modeltranslation.translator import translator
from modeltranslation.utils import get_translation_fields, build_localized_fieldname
# Ensure that models are registered for translation before TranslationAdmin
# runs. The import is supposed to resolve a race condition between model import
# and translation registration in production (see issue 19).
import modeltranslation.models


class TranslationAdminBase(object):
    """
    Mixin class which adds patch_translation_field functionality.
    """
    orig_was_required = {}

    def patch_translation_field(self, db_field, field, **kwargs):
        trans_opts = translator.get_options_for_model(self.model)

        # Hide the original field by making it non-editable.
        if db_field.name in trans_opts.fields:
            db_field.editable = False

            if field.required:
                field.required = False
                field.blank = True
                self.orig_was_required[\
                '%s.%s' % (db_field.model._meta, db_field.name)] = True

        # For every localized field copy the widget from the original field
        # and add a css class to identify a modeltranslation widget.
        if db_field.name in trans_opts.localized_fieldnames_rev:
            orig_fieldname = trans_opts.localized_fieldnames_rev[db_field.name]
            orig_formfield = self.formfield_for_dbfield(\
                             self.model._meta.get_field(orig_fieldname),
                                                        **kwargs)
            field.widget = copy(orig_formfield.widget)
            css_classes = field.widget.attrs.get('class', '').split(' ')
            css_classes.append('modeltranslation')

            if db_field.language == DEFAULT_LANGUAGE:
                # Add another css class to identify a default modeltranslation
                # widget.
                css_classes.append('modeltranslation-default')
                if orig_formfield.required or\
                   self.orig_was_required.get('%s.%s' % (db_field.model._meta,
                                                         orig_fieldname)):
                    # In case the original form field was required, make the
                    # default translation field required instead.
                    orig_formfield.required = False
                    orig_formfield.blank = True
                    field.required = True
                    field.blank = False

            field.widget.attrs['class'] = ' '.join(css_classes)


class TranslationAdmin(admin.ModelAdmin, TranslationAdminBase):
    def __init__(self, *args, **kwargs):
        super(TranslationAdmin, self).__init__(*args, **kwargs)
        trans_opts = translator.get_options_for_model(self.model)

        # Replace original field with translation field for each language
        if self.fields:
            fields_new = list(self.fields)
            for field in self.fields:
                if field in trans_opts.fields:
                    index = fields_new.index(field)
                    translation_fields = get_translation_fields(field)
                    fields_new[index:index + 1] = translation_fields
            self.fields = fields_new

        if self.fieldsets:
            fieldsets_new = list(self.fieldsets)
            for (name, dct) in self.fieldsets:
                if 'fields' in dct:
                    fields_new = list(dct['fields'])
                    for field in dct['fields']:
                        if field in trans_opts.fields:
                            index = fields_new.index(field)
                            translation_fields = get_translation_fields(field)
                            fields_new[index:index + 1] = translation_fields
                    dct['fields'] = fields_new
            self.fieldsets = fieldsets_new

        if self.list_editable:
            editable_new = list(self.list_editable)
            display_new = list(self.list_display)
            for field in self.list_editable:
                if field in trans_opts.fields:
                    index = editable_new.index(field)
                    display_index = display_new.index(field)
                    translation_fields = get_translation_fields(field)
                    editable_new[index:index + 1] = translation_fields
                    display_new[display_index:display_index + 1] =\
                    translation_fields
            self.list_editable = editable_new
            self.list_display = display_new

        if self.prepopulated_fields:
            prepopulated_fields_new = dict(self.prepopulated_fields)
            for (k, v) in self.prepopulated_fields.items():
                if v[0] in trans_opts.fields:
                    translation_fields = get_translation_fields(v[0])
                    prepopulated_fields_new[k] = tuple([translation_fields[0]])
            self.prepopulated_fields = prepopulated_fields_new

    def save_model(self, request, obj, form, change):
        # Rule is: 3. Assigning a value to a translation field of the default language also
        # updates the original field.
        # Ensure that an empty default language field value clears the default field.
        # See issue 47 for details.
        trans_opts = translator.get_options_for_model(self.model)
        for k, v in trans_opts.localized_fieldnames.items():
            if getattr(obj, k):
                default_lang_fieldname = build_localized_fieldname(k, DEFAULT_LANGUAGE)
                if not getattr(obj, default_lang_fieldname):
                    # TODO: Handle null values
                    setattr(obj, k, "")
        super(TranslationAdmin, self).save_model(request, obj, form, change)

    def formfield_for_dbfield(self, db_field, **kwargs):
        # Call the baseclass function to get the formfield
        field = super(TranslationAdmin, self).formfield_for_dbfield(db_field,
                                                                    **kwargs)
        self.patch_translation_field(db_field, field, **kwargs)
        return field


class TranslationTabularInline(admin.TabularInline, TranslationAdminBase):
    def formfield_for_dbfield(self, db_field, **kwargs):
        # Call the baseclass function to get the formfield
        field = super(TranslationTabularInline,
                      self).formfield_for_dbfield(db_field, **kwargs)
        self.patch_translation_field(db_field, field, **kwargs)
        return field


class TranslationStackedInline(admin.StackedInline, TranslationAdminBase):
    def formfield_for_dbfield(self, db_field, **kwargs):
        # Call the baseclass function to get the formfield
        field = super(TranslationStackedInline,
                      self).formfield_for_dbfield(db_field, **kwargs)
        self.patch_translation_field(db_field, field, **kwargs)
        return field


class TranslationGenericTabularInline(generic.GenericTabularInline,
                                      TranslationAdminBase):
    def formfield_for_dbfield(self, db_field, **kwargs):
        # Call the baseclass function to get the formfield
        field = super(TranslationGenericTabularInline,
                      self).formfield_for_dbfield(db_field, **kwargs)
        self.patch_translation_field(db_field, field, **kwargs)
        return field


class TranslationGenericStackedInline(generic.GenericStackedInline,
                                      TranslationAdminBase):
    def formfield_for_dbfield(self, db_field, **kwargs):
        # Call the baseclass function to get the formfield
        field = super(TranslationGenericStackedInline,
                      self).formfield_for_dbfield(db_field, **kwargs)
        self.patch_translation_field(db_field, field, **kwargs)
        return field
