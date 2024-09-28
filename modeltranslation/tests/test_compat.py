# mypy: disable-error-code="import-not-found"
import pytest
from modeltranslation import translator


class TestDjangoModelUtils:
    """
    Test case for https://github.com/deschler/django-modeltranslation/issues/760
    """

    def test_soft_deletable_model(self):
        try:
            from model_utils.models import SoftDeletableModel
        except ImportError:
            pytest.skip("django-model-utils not installed")

        class M1(SoftDeletableModel):
            pass

        @translator.register(M1)
        class M1Options(translator.TranslationOptions):
            pass
