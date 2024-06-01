from modeltranslation import admin
from modeltranslation.tests import models


def test_translation_admin():
    class TestModelAdmin(admin.TranslationAdmin[models.TestModel]):
        pass

    class TestInlineModelAdmin(
        admin.TranslationInlineModelAdmin[models.ForeignKeyModel, models.TestModel]
    ):
        pass
