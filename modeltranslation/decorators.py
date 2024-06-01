from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, TypeVar
from collections.abc import Iterable

from django.db.models import Model

if TYPE_CHECKING:
    from modeltranslation.translator import TranslationOptions

    _TranslationOptionsTypeT = TypeVar("_TranslationOptionsTypeT", bound=type[TranslationOptions])


def register(
    model_or_iterable: type[Model] | Iterable[type[Model]], **options: Any
) -> Callable[[_TranslationOptionsTypeT], _TranslationOptionsTypeT]:
    """
    Registers the given model(s) with the given translation options.

    The model(s) should be Model classes, not instances.

    Fields declared for translation on a base class are inherited by
    subclasses. If the model or one of its subclasses is already
    registered for translation, this will raise an exception.

    @register(Author)
    class AuthorTranslation(TranslationOptions):
        pass
    """
    from modeltranslation.translator import TranslationOptions, translator

    def wrapper(opts_class: _TranslationOptionsTypeT) -> _TranslationOptionsTypeT:
        if not issubclass(opts_class, TranslationOptions):
            raise ValueError("Wrapped class must subclass TranslationOptions.")
        translator.register(model_or_iterable, opts_class, **options)
        return opts_class

    return wrapper
