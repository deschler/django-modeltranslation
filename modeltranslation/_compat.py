from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

import django
from typing import Iterable
from typing import Optional

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.db.models.fields.reverse_related import ForeignObjectRel

_django_version = django.VERSION[:2]


def is_hidden(field: ForeignObjectRel) -> bool:
    return field.hidden


def clear_ForeignObjectRel_caches(field: ForeignObjectRel):
    """
    Django 5.1 Introduced caching for `accessor_name` props.

    We need to clear this cache when creating Translated field.

    https://github.com/django/django/commit/5e80390add100e0c7a1ac8e51739f94c5d706ea3#diff-e65b05ecbbe594164125af53550a43ef8a174f80811608012bc8e9e4ed575749
    """
    caches = ("accessor_name",)
    for name in caches:
        field.__dict__.pop(name, None)


def build_refresh_from_db(
    old_refresh_from_db: Callable[
        [Any, Optional[str], Optional[Iterable[str]], QuerySet[Any] | None], None
    ],
):
    from modeltranslation.manager import append_translated

    def refresh_from_db(
        self: Any,
        using: str | None = None,
        fields: Iterable[str] | None = None,
        from_queryset: QuerySet[Any] | None = None,
    ) -> None:
        if fields is not None:
            fields = append_translated(self.__class__, fields)
        return old_refresh_from_db(self, using, fields, from_queryset)

    return refresh_from_db


if _django_version <= (5, 0):

    def is_hidden(field: ForeignObjectRel) -> bool:
        return field.is_hidden()

    # Django versions below 5.1 do not have `from_queryset` argument.
    def build_refresh_from_db(  # type: ignore[misc]
        old_refresh_from_db: Callable[[Any, Optional[str], Optional[Iterable[str]]], None],
    ):
        from modeltranslation.manager import append_translated

        def refresh_from_db(
            self: Any,
            using: str | None = None,
            fields: Iterable[str] | None = None,
        ) -> None:
            if fields is not None:
                fields = append_translated(self.__class__, fields)
            return old_refresh_from_db(self, using, fields)

        return refresh_from_db
