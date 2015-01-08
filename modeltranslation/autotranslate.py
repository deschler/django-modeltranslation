# -*- coding: utf-8 -*-
from modeltranslation.translator import TranslationOptions
from django.db import models


def autotranslationoptionsfactory(model, include=[], exclude=[]):
    """
    Inline creation of TranslationOptions, with all TextField and Charfields automatically added.
    Takes 2 optional arguments 'include' and 'exclude', both lists of field names that should be
    included or excluded.
    Returns AutoTranslationOptions class, which inherits from TranslationOptions, with appropriate
    fields set.

    Example:

        from modeltranslation.autotranslate import autotranslationoptionsfactory

        for model in ModelClass1, ModelClass2, ModelClass3, ModelClass4, ModelClassN:
            translator.register(
                model,
                autotranslationoptionsfactory(model),
                include=['image'],
                exclude=['countrycode'])
    """

    class AutoTranslationOptions(TranslationOptions):
        fields = []
        for field in model._meta.fields:
            if field.__class__ in (models.TextField, models.CharField):
                if field.name not in exclude:
                    fields.append(field.name)
        for name in include:
            fields.append(name)

    return AutoTranslationOptions