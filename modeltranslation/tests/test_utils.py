from modeltranslation.utils import localized_cached_property, get_language
from django.utils.translation import override


def test_localized_cached_property():
    class Foo:
        @localized_cached_property
        def bar(self):
            return get_language()

    instance = Foo()

    for lang in ["en", "de"]:
        with override(lang):
            assert instance.bar == lang
