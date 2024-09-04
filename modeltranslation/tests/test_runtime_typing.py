from typing import get_type_hints

from modeltranslation import admin, translator
from modeltranslation.tests import models


def test_translation_admin():
    class TestModelAdmin(admin.TranslationAdmin[models.TestModel]):
        pass

    class TestInlineModelAdmin(
        admin.TranslationInlineModelAdmin[models.ForeignKeyModel, models.TestModel]
    ):
        pass


def test_type_hints():
    get_type_hints(translator.TranslationOptions)
    get_type_hints(admin.TranslationAdmin)
    get_type_hints(admin.TranslationInlineModelAdmin)
