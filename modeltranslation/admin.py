# -*- coding: utf-8 -*-
from copy import deepcopy

from django.contrib import admin
from django.contrib.admin.options import BaseModelAdmin, flatten_fieldsets, InlineModelAdmin
from django.contrib.contenttypes import generic

# Ensure that models are registered for translation before TranslationAdmin
# runs. The import is supposed to resolve a race condition between model import
# and translation registration in production (see issue #19).
import modeltranslation.models  # NOQA
from modeltranslation.settings import DEFAULT_LANGUAGE
from modeltranslation.translator import translator
from modeltranslation.utils import (
    get_translation_fields, build_css_class, build_localized_fieldname, get_language)


class TranslationBaseModelAdmin(BaseModelAdmin):
    _orig_was_required = {}

    def __init__(self, *args, **kwargs):
        super(TranslationBaseModelAdmin, self).__init__(*args, **kwargs)
        self.trans_opts = translator.get_options_for_model(self.model)
        self._patch_prepopulated_fields()

    def _declared_fieldsets(self):
        # Take custom modelform fields option into account
        if not self.fields and hasattr(self.form, '_meta') and self.form._meta.fields:
            self.fields = self.form._meta.fields
        if self.fieldsets:
            return self._patch_fieldsets(self.fieldsets)
        elif self.fields:
            return [(None, {'fields': self.replace_orig_field(self.fields)})]
        return None
    declared_fieldsets = property(_declared_fieldsets)

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super(TranslationBaseModelAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        self.patch_translation_field(db_field, field, **kwargs)
        return field

    def patch_translation_field(self, db_field, field, **kwargs):
        if db_field.name in self.trans_opts.fields:
            if field.required:
                field.required = False
                field.blank = True
                self._orig_was_required['%s.%s' % (db_field.model._meta, db_field.name)] = True

        # For every localized field copy the widget from the original field
        # and add a css class to identify a modeltranslation widget.
        try:
            orig_field = db_field.translated_field
        except AttributeError:
            pass
        else:
            orig_formfield = self.formfield_for_dbfield(orig_field, **kwargs)
            field.widget = deepcopy(orig_formfield.widget)
            css_classes = field.widget.attrs.get('class', '').split(' ')
            css_classes.append('mt')
            # Add localized fieldname css class
            css_classes.append(build_css_class(db_field.name, 'mt-field'))

            if db_field.language == DEFAULT_LANGUAGE:
                # Add another css class to identify a default modeltranslation
                # widget.
                css_classes.append('mt-default')
                if (orig_formfield.required or self._orig_was_required.get(
                        '%s.%s' % (orig_field.model._meta, orig_field.name))):
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
            return exclude_new + tuple(self.trans_opts.fields.keys())
        return tuple(self.trans_opts.fields.keys())

    def replace_orig_field(self, option):
        """
        Replaces each original field in `option` that is registered for
        translation by its translation fields.

        Returns a new list with replaced fields. If `option` contains no
        registered fields, it is returned unmodified.

        >>> print self.trans_opts.fields.keys()
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
            for opt in option:
                if opt in self.trans_opts.fields:
                    index = option_new.index(opt)
                    option_new[index:index + 1] = get_translation_fields(opt)
                elif isinstance(opt, (tuple, list)) and (
                        [o for o in opt if o in self.trans_opts.fields]):
                    index = option_new.index(opt)
                    option_new[index:index + 1] = self.replace_orig_field(opt)
            option = option_new
        return option

    def _patch_fieldsets(self, fieldsets):
        if fieldsets:
            fieldsets_new = list(fieldsets)
            for (name, dct) in fieldsets:
                if 'fields' in dct:
                    dct['fields'] = self.replace_orig_field(dct['fields'])
            fieldsets = fieldsets_new
        return fieldsets

    def _patch_prepopulated_fields(self):
        if self.prepopulated_fields:
            # TODO: Perhaps allow to configure which language the slug should be based on?
            lang = get_language()
            prepopulated_fields_new = dict(self.prepopulated_fields)
            translation_fields = []
            for k, v in self.prepopulated_fields.items():
                for i in v:
                    if i in self.trans_opts.fields.keys():
                        translation_fields.append(build_localized_fieldname(i, lang))
                prepopulated_fields_new[k] = tuple(translation_fields)
            self.prepopulated_fields = prepopulated_fields_new

    def _do_get_form_or_formset(self, request, obj, **kwargs):
        """
        Code shared among get_form and get_formset.
        """
        if self.exclude is None:
            exclude = []
        else:
            exclude = list(self.exclude)
        exclude.extend(self.get_readonly_fields(request, obj))
        if not self.exclude and hasattr(self.form, '_meta') and self.form._meta.exclude:
            # Take the custom ModelForm's Meta.exclude into account only if the
            # ModelAdmin doesn't define its own.
            exclude.extend(self.form._meta.exclude)
        # If exclude is an empty list we pass None to be consistant with the
        # default on modelform_factory
        exclude = self.replace_orig_field(exclude) or None
        exclude = self._exclude_original_fields(exclude)
        kwargs.update({'exclude': exclude})

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
        fields = base_fields + list(self.get_readonly_fields(request, obj))
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
        for orig_fieldname, translation_fields in self.trans_opts.fields.iteritems():
            for tfield in translation_fields:
                language = tfield.name.split('_')[-1]
                if language in excl_languages and tfield not in exclude:
                    exclude.append(tfield)
        return tuple(exclude)

    def get_readonly_fields(self, request, obj=None):
        """
        Hook for specifying custom readonly fields.
        """
        return self.replace_orig_field(self.readonly_fields)


class TranslationAdmin(TranslationBaseModelAdmin, admin.ModelAdmin):
    # TODO: Consider addition of a setting which allows to override the fallback to True
    group_fieldsets = False

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
                    display_new[display_index:display_index + 1] = translation_fields
            self.list_editable = editable_new
            self.list_display = display_new

    def _group_fieldsets(self, fieldsets):
        # Fieldsets are not grouped by default. The function is activated by
        # setting TranslationAdmin.group_fieldsets to True. If the admin class
        # already defines a fieldset, we leave it alone and assume the author
        # has done whatever grouping for translated fields they desire.
        if not self.declared_fieldsets and self.group_fieldsets is True:
            flattened_fieldsets = flatten_fieldsets(fieldsets)

            # Create a fieldset to group each translated field's localized fields
            untranslated_fields = [
                f.name for f in self.opts.fields if (
                    # Exclude the primary key field
                    f is not self.opts.auto_field
                    # Exclude non-editable fields
                    and f.editable
                    # Exclude the translation fields
                    # TODO: I already miss localized_fieldnames_rev here ;)
                    and f not in [
                        k for l in [list(j) for i in self.trans_opts.fields.items() for
                                    j in i[1:]] for k in l]
                    # Honour field arguments. We rely on the fact that the
                    # passed fieldsets argument is already fully filtered
                    # and takes options like exclude into account.
                    and f.name in flattened_fieldsets
                )
            ]
            # TODO: Allow setting a label
            fieldsets = [('', {'fields': untranslated_fields},)] if untranslated_fields else []

            for orig_field, trans_fields in self.trans_opts.fields.items():
                trans_fieldnames = [f.name for f in sorted(trans_fields, key=lambda x: x.name)]
                if any(f in trans_fieldnames for f in flattened_fieldsets):
                    # Extract the original field's verbose_name for use as this
                    # fieldset's label - using ugettext_lazy in your model
                    # declaration can make that translatable.
                    label = self.model._meta.get_field(orig_field).verbose_name
                    fieldsets.append((label, {
                        'fields': trans_fieldnames,
                        'classes': ('mt-fieldset',)
                    }))

        return fieldsets

    def get_form(self, request, obj=None, **kwargs):
        kwargs = self._do_get_form_or_formset(request, obj, **kwargs)
        return super(TranslationAdmin, self).get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        if self.declared_fieldsets:
            return self._do_get_fieldsets_pre_form_or_formset()
        return self._group_fieldsets(
            self._do_get_fieldsets_post_form_or_formset(request, self.get_form(request, obj), obj))


class TranslationInlineModelAdmin(TranslationBaseModelAdmin, InlineModelAdmin):
    def get_formset(self, request, obj=None, **kwargs):
        kwargs = self._do_get_form_or_formset(request, obj, **kwargs)
        return super(TranslationInlineModelAdmin, self).get_formset(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        # FIXME: If fieldsets are declared on an inline some kind of ghost
        # fieldset line with just the original model verbose_name of the model
        # is displayed above the new fieldsets.
        if self.declared_fieldsets:
            return self._do_get_fieldsets_pre_form_or_formset()
        form = self.get_formset(request, obj).form
        return self._do_get_fieldsets_post_form_or_formset(request, form, obj)


class TranslationTabularInline(TranslationInlineModelAdmin, admin.TabularInline):
    pass


class TranslationStackedInline(TranslationInlineModelAdmin, admin.StackedInline):
    pass


class TranslationGenericTabularInline(TranslationInlineModelAdmin, generic.GenericTabularInline):
    pass


class TranslationGenericStackedInline(TranslationInlineModelAdmin, generic.GenericStackedInline):
    pass
