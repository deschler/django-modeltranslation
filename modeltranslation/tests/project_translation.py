from modeltranslation.translator import translator, TranslationOptions
from test_app.models import Other


class OtherTranslationOptions(TranslationOptions):
    fields = ('name',)

translator.register(Other, OtherTranslationOptions)
