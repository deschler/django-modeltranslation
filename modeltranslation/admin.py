# -*- coding: utf-8 -*-
from copy import deepcopy

from django import forms, template
from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes import generic

from modeltranslation.translator import translator
from modeltranslation.utils import get_translation_fields

class TranslationAdminBase(object):
    """
    Mixin class which adds patch_translation_field functionality.
    """
    def patch_translation_field(self, db_field, field, **kwargs):
        trans_opts = translator.get_options_for_model(self.model)        
        
        # Hide the original field by making it non-editable.
        if db_field.name in trans_opts.fields:
            db_field.editable = False
        
        # For every localized field copy the widget from the original field
        if db_field.name in trans_opts.localized_fieldnames_rev:
            orig_fieldname = trans_opts.localized_fieldnames_rev[db_field.name]
            orig_formfield = self.formfield_for_dbfield(self.model._meta.get_field(orig_fieldname), **kwargs)

            # In case the original form field was required, make the default
            # translation field required instead.
            if db_field.language == settings.LANGUAGES[0][0] and orig_formfield.required:
                orig_formfield.required = False
                field.required = True
                                            
            field.widget = deepcopy(orig_formfield.widget) 


class TranslationAdmin(admin.ModelAdmin, TranslationAdminBase):
    def __init__(self, *args, **kwargs):
        super(TranslationAdmin, self).__init__(*args, **kwargs)
      
        # Replace original field with translation field for each language
        if self.fields or self.fieldsets:
            trans_opts = translator.get_options_for_model(self.model)
            if self.fields:
                fields_new = list(self.fields)
                for field in self.fields:
                    if field in trans_opts.fields:
                        index = fields_new.index(field)
                        translation_fields = get_translation_fields(field)
                        fields_new = self.fields[:index] + translation_fields + self.fields[index+1:]
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
                                fields_new = fields_new[:index] + translation_fields + fields_new[index+1:]
                        dct['fields'] = fields_new
                self.fieldsets = fieldsets_new
                
    def formfield_for_dbfield(self, db_field, **kwargs):
        # Call the baseclass function to get the formfield        
        field = super(TranslationAdmin, self).formfield_for_dbfield(db_field, **kwargs)        
        self.patch_translation_field(db_field, field, **kwargs)
        return field

    
class TranslationTabularInline(admin.TabularInline, TranslationAdminBase):
    def formfield_for_dbfield(self, db_field, **kwargs):
        # Call the baseclass function to get the formfield        
        field = super(TranslationTabularInline, self).formfield_for_dbfield(db_field, **kwargs)        
        self.patch_translation_field(db_field, field, **kwargs)
        return field            


class TranslationStackedInline(admin.StackedInline, TranslationAdminBase):
    def formfield_for_dbfield(self, db_field, **kwargs):
        # Call the baseclass function to get the formfield        
        field = super(TranslationStackedInline, self).formfield_for_dbfield(db_field, **kwargs)        
        self.patch_translation_field(db_field, field, **kwargs)
        return field            


class TranslationGenericTabularInline(generic.GenericTabularInline, TranslationAdminBase):
    def formfield_for_dbfield(self, db_field, **kwargs):
        # Call the baseclass function to get the formfield        
        field = super(TranslationGenericTabularInline, self).formfield_for_dbfield(db_field, **kwargs)        
        self.patch_translation_field(db_field, field, **kwargs)
        return field            


class TranslationGenericStackedInline(generic.GenericStackedInline, TranslationAdminBase):
    def formfield_for_dbfield(self, db_field, **kwargs):
        # Call the baseclass function to get the formfield        
        field = super(TranslationGenericStackedInline, self).formfield_for_dbfield(db_field, **kwargs)        
        self.patch_translation_field(db_field, field, **kwargs)
        return field            
