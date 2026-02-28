from modeltranslation.tests import models


class TestFieldOptions:
    def test_explicit_language_option_applied(self):
        """field_options entry for a specific language is set on that language's field."""
        field = models.FieldOptionsModel._meta.get_field("title_en")
        assert field.db_index is True

    def test_default_option_applied_to_unlisted_language(self):
        """The 'default' key applies to languages not explicitly listed."""
        assert models.FieldOptionsModel._meta.get_field("title_de").db_index is False
        assert models.FieldOptionsModel._meta.get_field("sub_title2_en").db_index is True

    def test_explicit_language_wins_over_default(self):
        """An explicit language entry must take precedence over 'default'."""
        assert models.FieldOptionsModel._meta.get_field("title_en").db_index is True
        assert models.FieldOptionsModel._meta.get_field("title_de").db_index is False
        assert models.FieldOptionsModel._meta.get_field("sub_title2_de").db_index is False
        assert models.FieldOptionsModel._meta.get_field("sub_title2_en").db_index is True

    def test_field_options_on_second_field(self):
        """field_options works independently for each declared field."""
        assert models.FieldOptionsModel._meta.get_field("sub_title1_de").db_index is True

    def test_unlisted_language_without_default_is_unchanged(self):
        """When there is no explicit entry and no 'default', the field is not modified."""
        # slug has 'de' but no 'default'; sub_title1_en must keep SlugField's default (False)
        assert models.FieldOptionsModel._meta.get_field("sub_title1_en").db_index is False

    def test_deconstruct_includes_per_language_kwarg(self):
        """deconstruct() must expose per-language options so migrations serialise them."""
        field = models.FieldOptionsModel._meta.get_field("title_en")
        _name, _path, _args, kwargs = field.deconstruct()
        assert "db_index" in kwargs
        assert kwargs["db_index"] is True

    def test_deconstruct_default_kwarg_included(self):
        """The field carrying the 'default' option also appears correctly in deconstruct()."""
        field = models.FieldOptionsModel._meta.get_field("title_de")
        _name, _path, _args, kwargs = field.deconstruct()
        assert "db_index" in kwargs
        assert kwargs["db_index"] is False

    def test_deconstruct_no_extra_kwargs_without_field_options(self):
        """Fields on models without field_options must not gain extra kwargs in deconstruct()."""
        field = models.TestModel._meta.get_field("title_en")
        _name, _path, _args, kwargs = field.deconstruct()
        assert "db_index" not in kwargs

    def test_model_without_field_options_unaffected(self):
        """Models that don't use field_options continue to work as before."""
        field_en = models.TestModel._meta.get_field("title_en")
        field_de = models.TestModel._meta.get_field("title_de")
        assert field_en.db_index == field_de.db_index
