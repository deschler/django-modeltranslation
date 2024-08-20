from __future__ import annotations

from typing import TYPE_CHECKING

import django

if TYPE_CHECKING:
    from django.db.models.fields.reverse_related import ForeignObjectRel


def is_hidden(field: ForeignObjectRel) -> bool:
    return field.hidden


if django.VERSION <= (5, 1):

    def is_hidden(field: ForeignObjectRel) -> bool:
        return field.is_hidden()
