# -*- coding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext_lazy as _

from modeltranslation.fields import TranslationField


class TranslationModelForm(forms.ModelForm):
    """
    This form removes the localized fields from the form. The values
    introduced will be automatically used for the active language.
    """

    def __init__(self, *args, **kwargs):
        super(TranslationModelForm, self).__init__(*args, **kwargs)
        for f in self._meta.model._meta.fields:
            if f.name in self.fields and isinstance(f, TranslationField):
                del self.fields[f.name]


class FreeTranslationModelForm(forms.ModelForm):
    """
    This form gives more freedom to the user to introduce the
    translations he wants.
    For the required translatable fields at least one translation
    must be populated. But, if the translatable field is not required,
    all translations may be left blank.
    """

    def __init__(self, *args, **kwargs):
        super(FreeTranslationModelForm, self).__init__(*args, **kwargs)
        self.exclude_trans = []  # Each item is the original name of the non required trans fields
        self.translated_fields = []  # Each item is a list of the translations for one field
        translations = []  # Actual translations list for a translatable field
        for field in self._meta.model._meta.fields:
            if field.name in self.fields and isinstance(field, TranslationField):
                original_field = self._original_fieldname(field.name)
                if not translations or self._original_fieldname(translations[-1]) == original_field:
                    translations.append(field.name)
                else:
                    self.translated_fields.append(translations)
                    translations = [field.name]
                if original_field in self.fields:
                    # We are now sure that it has not been already deleted
                    # by another language translation
                    if not self.fields[original_field].required:
                        self.exclude_trans.append(original_field)
                    del self.fields[original_field]
        if translations:
            self.translated_fields.append(translations)

    def _original_fieldname(self, translated_field):
        return translated_field[:-3]  # Removes lang code

    def clean(self):
        cleaned_data = super(FreeTranslationModelForm, self).clean()
        untranslated_fields = []
        for field in self.translated_fields:
            has_translation = False
            for translation in field:
                if cleaned_data.get(translation):
                    has_translation = True
                    break
            if not has_translation and not self._original_fieldname(field[0]) in self.exclude_trans:
                untranslated_fields.append(self.fields[field[0]].label[:-5])
        if untranslated_fields:
            raise forms.ValidationError(_("Enter at least one translation for:") + " " + \
                ", ".join(untranslated_fields))
        return cleaned_data
