from django.contrib.admin import site
from models import Category
from modeltranslation.admin import TranslationAdmin


class CategoryAdmin(TranslationAdmin):
    pass

site.register(Category, CategoryAdmin)
