from __future__ import annotations

from typing import TYPE_CHECKING

import django

if TYPE_CHECKING:
    from django.db.models.fields.reverse_related import ForeignObjectRel


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


if django.VERSION <= (5, 1):

    def is_hidden(field: ForeignObjectRel) -> bool:
        return field.is_hidden()
