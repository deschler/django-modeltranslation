import sys
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


@pytest.mark.skipif(
    sys.version_info < (3, 10), 
    reason="get_type_hints fails on Python 3.9 despite future annotations",
)
def test_type_hints():
    get_type_hints(translator.TranslationOptions)
    get_type_hints(admin.TranslationAdmin)
    get_type_hints(admin.TranslationInlineModelAdmin)
