# -*- coding: utf-8 -*-
from copy import deepcopy

from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.forms import widgets
from django import forms, template
from django.forms.fields import MultiValueField
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.safestring import mark_safe

from modeltranslation.translator import translator


class TranslationAdmin(admin.ModelAdmin):
                
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
        
    def formfield_for_dbfield(self, db_field, **kwargs):
        # Call the baseclass function to get the formfield        
        field = super(TranslationAdmin, self).formfield_for_dbfield(db_field, **kwargs)        
        self.patch_translation_field(db_field, field, **kwargs)
        return field
                            
    #def save_model(self, request, obj, form, change):
        #"""
        #Given a model instance save it to the database.
        
        #Because each translated field is wrapped with a descriptor to return 
        #the translated fields value (determined by the current language) we 
        #cannot set the field directly.
        #To bypass the descriptor the assignment is done using the __dict__
        #of the object.
        #"""                                
        #trans_opts = translator.get_options_for_model(self.model)
        #for field_name in trans_opts.fields:
            ## Bypass the descriptor applied to the original field by setting
            ## it's value via the __dict__ (which doesn't call the descriptor).
            #obj.__dict__[field_name] = form.cleaned_data[field_name]
            
        ## Call the baseclass method            
        #super(TranslationAdmin, self).save_model(request, obj, form, change)

        
class TranslationTabularInline(admin.TabularInline):

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

    def formfield_for_dbfield(self, db_field, **kwargs):
        # Call the baseclass function to get the formfield        
        field = super(TranslationTabularInline, self).formfield_for_dbfield(db_field, **kwargs)        
        self.patch_translation_field(db_field, field, **kwargs)
        return field            


class TranslationStackedInline(admin.StackedInline):

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

    def formfield_for_dbfield(self, db_field, **kwargs):
        # Call the baseclass function to get the formfield        
        field = super(TranslationStackedInline, self).formfield_for_dbfield(db_field, **kwargs)        
        self.patch_translation_field(db_field, field, **kwargs)
        return field            
        