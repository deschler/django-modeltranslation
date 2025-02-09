from modeltranslation import translator

from .test_app import models


@translator.register(models.Other)
class OtherTranslationOptions(translator.TranslationOptions):
    fields = ("name",)
