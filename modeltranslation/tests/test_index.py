from modeltranslation.tests import models


class TestIndexPatching:
    def _index_fields(self, model):
        return [tuple(idx.fields) for idx in model._meta.indexes]

    def _index_names(self, model):
        return {idx.name for idx in model._meta.indexes if idx.name}

    def test_translated_field_index_is_expanded(self):
        fields = self._index_fields(models.ModelWithIndex)
        assert ("title",) in fields
        assert ("title_en",) in fields
        assert ("title_de",) in fields

    def test_multi_field_index_both_translated_is_expanded(self):
        fields = self._index_fields(models.ModelWithIndex)
        assert ("title", "sub_title") in fields
        assert ("title_en", "sub_title_en") in fields
        assert ("title_de", "sub_title_de") in fields

    def test_non_translated_field_index_is_unchanged(self):
        fields = self._index_fields(models.ModelWithIndex)
        names = self._index_names(models.ModelWithIndex)
        assert ("email",) in fields
        assert "idx_email" in names

    def test_expanded_index_names_contain_language_code(self):
        names = self._index_names(models.ModelWithIndex)
        assert any("en" in n for n in names)
        assert any("de" in n for n in names)

    def test_unnamed_index_on_translated_field_is_expanded(self):
        fields = self._index_fields(models.ModelWithIndex)
        assert ("sub_title_en",) in fields
        assert ("sub_title_de",) in fields
        assert ("sub_title",) in fields

    def test_indexes_preserves_subclass(self):
        idx_custom = [
            idx for idx in models.ModelWithIndex._meta.indexes if idx.name.startswith("idx_custom")
        ]
        assert all(type(idx) is models.CustomIndex for idx in idx_custom)

    def test_total_index_count_is_correct(self):
        # idx_title:           1 original + 2 languages = 3
        # idx_title_sub_title: 1 original + 2 languages = 3
        # sub_title:           1 original + 2 languages = 3
        # email:               1 original               = 1
        # custom:              1 original + 2 languages = 3
        assert len(models.ModelWithIndex._meta.indexes) == 13
