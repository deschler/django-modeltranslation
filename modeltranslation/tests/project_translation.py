from modeltranslation.translator import TranslationOptions, translator

from .test_app.models import Other


class OtherTranslationOptions(TranslationOptions):
    fields = ('name',)


translator.register(Other, OtherTranslationOptions)
