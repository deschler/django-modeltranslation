from modeltranslation.translator import translator, TranslationOptions
from models import News


class NewsTranslationOptions(TranslationOptions):
    fields = ('title',)

translator.register(News, NewsTranslationOptions)
