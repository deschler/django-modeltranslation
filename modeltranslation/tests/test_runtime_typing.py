from typing import get_type_hints

import pytest

from modeltranslation import admin, translator
from modeltranslation.tests import models


def test_translation_admin():
    class TestModelAdmin(admin.TranslationAdmin[models.TestModel]):
        pass

    class TestInlineModelAdmin(
        admin.TranslationInlineModelAdmin[models.ForeignKeyModel, models.TestModel]
    ):
        pass


@pytest.mark.parametrize(
    "cls",
    [
        translator.TranslationOptions,
        admin.TranslationAdmin,
        admin.TranslationInlineModelAdmin,
    ],
)
def test_type_hints(cls):
    get_type_hints(cls)
