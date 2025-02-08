from modeltranslation import translator

from . import models


@translator.register(models.News)
class NewsTranslationOptions(translator.TranslationOptions):
    fields = ("title",)
