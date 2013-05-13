# -*- coding: utf-8 -*-
from django import forms

from modeltranslation.fields import TranslationField


class TranslationModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(TranslationModelForm, self).__init__(*args, **kwargs)
        for f in self._meta.model._meta.fields:
            if f.name in self.fields and isinstance(f, TranslationField):
                del self.fields[f.name]
