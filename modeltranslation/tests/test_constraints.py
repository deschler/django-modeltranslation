from django.db.models import UniqueConstraint

from modeltranslation.tests import models


class TestConstraints:
    def test_unique_together_translated_fields_are_expanded(self):
        unique_together = self._unique_together(models.ModelWithConstraint)
        assert ("title1", "sub_title1") in unique_together
        assert ("title1_en", "sub_title1_en") in unique_together
        assert ("title1_de", "sub_title1_de") in unique_together

    def test_unique_together_expands_per_language(self):
        unique_together = self._unique_together(models.ModelWithConstraint)
        assert ("title1_en", "sub_title1_en") in unique_together
        assert ("title1_de", "sub_title1_de") in unique_together

    def test_unique_together_total_count_is_correct(self):
        # 1 original + 1 per language (en, de)
        assert len(models.ModelWithConstraint._meta.unique_together) == 3

    def test_single_field_constraint_is_expanded(self):
        fields = self._constraint_fields(models.ModelWithConstraint)
        assert ("title2",) in fields
        assert ("title2_en",) in fields
        assert ("title2_de",) in fields

    def test_single_field_constraint_names_contain_language_code(self):
        names = self._constraint_names(models.ModelWithConstraint)
        assert "unique_sfield-en" in names
        assert "unique_sfield-de" in names

    def test_multi_field_constraint_both_translated_is_expanded(self):
        fields = self._constraint_fields(models.ModelWithConstraint)
        assert ("title3", "sub_title2") in fields
        assert ("title3_en", "sub_title2_en") in fields
        assert ("title3_de", "sub_title2_de") in fields

    def test_multi_field_constraint_names_contain_language_code(self):
        names = self._constraint_names(models.ModelWithConstraint)
        assert "unique_mfields-en" in names
        assert "unique_mfields-de" in names

    def test_multi_field_constraint_produces_one_constraint_per_language(self):
        fields = self._constraint_fields(models.ModelWithConstraint)
        assert ("title3_en", "sub_title2_de") not in fields
        assert ("title3_de", "sub_title2_en") not in fields

    def test_partial_translated_constraint_is_expanded(self):
        fields = self._constraint_fields(models.ModelWithConstraint)
        assert ("title3", "email") in fields
        assert ("title3_en", "email") in fields
        assert ("title3_de", "email") in fields

    def test_partial_translated_constraint_non_translated_field_is_unchanged(self):
        fields = self._constraint_fields(models.ModelWithConstraint)
        assert ("title3_en", "email_en") not in fields
        assert ("title3_de", "email_de") not in fields

    def test_partial_translated_constraint_names_contain_language_code(self):
        names = self._constraint_names(models.ModelWithConstraint)
        assert "unique_partfield-en" in names
        assert "unique_partfield-de" in names

    def test_constraints_preserves_subclass(self):
        constraints_custom = [
            c
            for c in models.ModelWithConstraint._meta.constraints
            if c.name.startswith("unique_custom")
        ]
        assert all(type(c) is models.CustomUniqueConstraint for c in constraints_custom)

    def test_total_constraint_count_is_correct(self):
        # unique_sfield:    1 original + 2 languages = 3
        # unique_mfields:   1 original + 2 languages = 3
        # unique_partfield: 1 original + 2 languages = 3
        # custom:           1 original + 2 languages = 3
        assert len(models.ModelWithConstraint._meta.constraints) == 12

    def _unique_together(self, model):
        return list(model._meta.unique_together)

    def _constraint_fields(self, model):
        return [tuple(c.fields) for c in model._meta.constraints if isinstance(c, UniqueConstraint)]

    def _constraint_names(self, model):
        return {c.name for c in model._meta.constraints if isinstance(c, UniqueConstraint)}
