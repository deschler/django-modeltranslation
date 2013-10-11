# -*- coding: utf-8 -*-
from django import forms

from modeltranslation.fields import TranslationField


class TranslationModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(TranslationModelForm, self).__init__(*args, **kwargs)
        for f in self._meta.model._meta.fields:
            if f.name in self.fields and isinstance(f, TranslationField):
                del self.fields[f.name]


class NullableField(object):
    """
    Form field mixin that ensures that ``None`` is not cast to anything (like
    the empty string with ``CharField`` and its derivatives).
    """
    def to_python(self, value):
        if value is None:
            return value
        return super(NullableField, self).to_python(value)

    # Django 1.6
    def _has_changed(self, initial, data):
        if (initial is None and data is not None) or (initial is not None and data is None):
            return True
        return super(NullableField, self)._has_changed(initial, data)
