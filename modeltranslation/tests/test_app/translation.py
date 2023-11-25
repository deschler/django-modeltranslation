from modeltranslation.translator import TranslationOptions, translator

from .models import News


class NewsTranslationOptions(TranslationOptions):
    fields = ("title",)


translator.register(News, NewsTranslationOptions)
