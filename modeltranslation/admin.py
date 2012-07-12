# -*- coding: utf-8 -*-
from copy import deepcopy

from django.contrib import admin
from django.contrib.admin.options import BaseModelAdmin, InlineModelAdmin
from django.contrib.contenttypes import generic
from django.utils import translation

from modeltranslation.settings import DEFAULT_LANGUAGE
from modeltranslation.translator import translator
from modeltranslation.utils import (get_translation_fields,
                                    build_localized_fieldname)


class TranslationBaseModelAdmin(BaseModelAdmin):
    _orig_was_required = {}

    def __init__(self, *args, **kwargs):
        super(TranslationBaseModelAdmin, self).__init__(*args, **kwargs)
        self.trans_opts = translator.get_options_for_model(self.model)
        self._patch_prepopulated_fields()

    def _declared_fieldsets(self):
        # Take custom modelform fields option into account
        if not self.fields and hasattr(
            self.form, '_meta') and self.form._meta.fields:
            self.fields = self.form._meta.fields
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
        if db_field.name in self.trans_opts.fields:
            if field.required:
                field.required = False
                field.blank = True
                self._orig_was_required[
                    '%s.%s' % (db_field.model._meta, db_field.name)] = True

        # For every localized field copy the widget from the original field
        # and add a css class to identify a modeltranslation widget.
        if db_field.name in self.trans_opts.localized_fieldnames_rev:
            orig_fieldname = self.trans_opts.localized_fieldnames_rev[
                db_field.name]
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

    def _patch_fieldsets(self, fieldsets):
        # TODO: Handle nested lists to display multiple fields on same line.
        if fieldsets:
            fieldsets_new = list(fieldsets)
            for (name, dct) in fieldsets:
                if 'fields' in dct:
                    dct['fields'] = self.replace_orig_field(dct['fields'])
            fieldsets = fieldsets_new
        return fieldsets

    def _patch_prepopulated_fields(self):
        if self.prepopulated_fields:
            prepopulated_fields_new = dict(self.prepopulated_fields)
            for (k, v) in self.prepopulated_fields.items():
                if v[0] in self.trans_opts.fields:
                    translation_fields = get_translation_fields(v[0])
                    prepopulated_fields_new[k] = tuple([translation_fields[0]])
            self.prepopulated_fields = prepopulated_fields_new

    def _do_get_form_or_formset(self, **kwargs):
        """
        Code shared among get_form and get_formset.
        """
        if not self.exclude and hasattr(
            self.form, '_meta') and self.form._meta.exclude:
            # Take the custom ModelForm's Meta.exclude into account only if the
            # ModelAdmin doesn't define its own.
            kwargs.update({'exclude': getattr(
                kwargs, 'exclude', tuple()) +
                tuple(self.replace_orig_field(self.form._meta.exclude))})
        exclude = kwargs.get('exclude', [])
        self.exclude = self.replace_orig_field(self.exclude)
        exclude_fields = (
            self._exclude_original_fields(exclude))
        if self.exclude:
            exclude_fields = tuple(self.exclude) + tuple(exclude_fields)
        if exclude_fields:
            kwargs.update({'exclude': getattr(
                kwargs, 'exclude', tuple()) + exclude_fields})

        return kwargs

    def _do_get_fieldsets_pre_form_or_formset(self):
        """
        Common get_fieldsets code shared among TranslationAdmin and
        TranslationInlineModelAdmin.
        """
        return self._declared_fieldsets()

    def _do_get_fieldsets_post_form_or_formset(self, request, form, obj=None):
        """
        Common get_fieldsets code shared among TranslationAdmin and
        TranslationInlineModelAdmin.
        """
        base_fields = self.replace_orig_field(form.base_fields.keys())
        fields = base_fields + list(
            self.get_readonly_fields(request, obj))
        return [(None, {'fields': self.replace_orig_field(fields)})]

    def get_translation_field_excludes(self, exclude_languages=None):
        """
        Returns a tuple of translation field names to exclude base on
        `exclude_languages` arg.
        """
        if exclude_languages is None:
            exclude_languages = []
        excl_languages = []
        if exclude_languages:
            excl_languages = exclude_languages
        exclude = []
        for orig_fieldname, translation_fields in \
            self.trans_opts.localized_fieldnames.iteritems():
            for tfield in translation_fields:
                language = tfield.split('_')[-1]
                if language in excl_languages and tfield not in exclude:
                    exclude.append(tfield)
        return tuple(exclude)


class TranslationAdmin(TranslationBaseModelAdmin, admin.ModelAdmin):
    def __init__(self, *args, **kwargs):
        super(TranslationAdmin, self).__init__(*args, **kwargs)
        self._patch_list_editable()

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

    def get_form(self, request, obj=None, **kwargs):
        kwargs = self._do_get_form_or_formset(**kwargs)
        return super(TranslationAdmin, self).get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        if self.declared_fieldsets:
            return self._do_get_fieldsets_pre_form_or_formset()
        form = self.get_form(request, obj)
        return self._do_get_fieldsets_post_form_or_formset(
            request, form, obj)

    def save_model(self, request, obj, form, change):
        # Rule is: 3. Assigning a value to a translation field of the default
        # language also updates the original field.
        # Ensure that an empty default language field value clears the original
        # field. See issue 47 for details.
        for k, v in self.trans_opts.localized_fieldnames.items():
            if getattr(obj, k):
                default_lang_fieldname = build_localized_fieldname(
                    k, DEFAULT_LANGUAGE)
                if not getattr(obj, default_lang_fieldname):
                    # TODO: Handle null values
                    setattr(obj, k, '')
        # HACK: Force default language for save
        # See issue 33 for details.
        current_lang = translation.get_language()
        translation.activate(DEFAULT_LANGUAGE)
        super(TranslationAdmin, self).save_model(request, obj, form, change)
        # Restore the former current language, just in case.
        translation.activate(current_lang)


class TranslationInlineModelAdmin(TranslationBaseModelAdmin, InlineModelAdmin):
    def get_formset(self, request, obj=None, **kwargs):
        kwargs = self._do_get_form_or_formset(**kwargs)
        return super(TranslationInlineModelAdmin, self).get_formset(
            request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        # FIXME: If fieldsets are declared on an inline some kind of ghost
        # fieldset line with just the original model verbose_name of the model
        # is displayed above the new fieldsets.
        if self.declared_fieldsets:
            return self._do_get_fieldsets_pre_form_or_formset()
        form = self.get_formset(request, obj).form
        return self._do_get_fieldsets_post_form_or_formset(
            request, form, obj)


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
