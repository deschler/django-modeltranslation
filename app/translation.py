from modeltranslation.translator import translator, TranslationOptions
from models import Category


class CategoryTO(TranslationOptions):
    fields = ('slug',)

translator.register(Category, CategoryTO)
