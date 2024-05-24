from __future__ import annotations

from typing import Any, ClassVar, Iterable

from modeltranslation.fields import TranslationField


class FieldsAggregationMetaClass(type):
    fields: ClassVar[Iterable[str]]

    def __new__(cls, name: str, bases: tuple[type, ...], attrs: dict[str, Any]) -> type: ...


class TranslationOptions(metaclass=FieldsAggregationMetaClass):
    def __init__(self) -> None:
        self.fields: dict[str, set[TranslationField]] = {f: set() for f in self.fields}


class BookTranslationOptions(TranslationOptions):
    fields = ["name"]
