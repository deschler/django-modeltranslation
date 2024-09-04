from __future__ import annotations

import sys
from typing import Literal, TypeVar, Union

from django.contrib import admin
from django.contrib.admin.options import BaseModelAdmin

if sys.version_info >= (3, 11):
    from typing import Self, TypeAlias  # noqa: F401
else:
    from typing_extensions import Self, TypeAlias  # noqa: F401

AutoPopulate: TypeAlias = "bool | Literal['all', 'default', 'required']"

_K = TypeVar("_K")

# See https://github.com/typeddjango/django-stubs/blob/082955/django-stubs/utils/datastructures.pyi#L12-L14
_ListOrTuple: TypeAlias = Union[list[_K], tuple[_K, ...]]


# https://github.com/typeddjango/django-stubs/tree/master/django_stubs_ext
# For generic classes to work at runtime we need to define `__class_getitem__`.
# We're defining it here, instead of relying on django_stubs_ext, because
# we don't want every user setting up django_stubs_ext just for this feature.
def monkeypatch() -> None:
    classes = [
        admin.ModelAdmin,
        BaseModelAdmin,
    ]

    def class_getitem(cls: type, key: str | type | TypeVar):
        if isinstance(key, str) and hasattr(cls, key):
            # Fix django-cms compatibility:
            # https://github.com/django-cms/django-cms/issues/7948
            raise KeyError(f"Key '{key}' found as attribute, use getattr to access it.")
        return cls

    for cls in classes:
        cls.__class_getitem__ = classmethod(class_getitem)  # type: ignore[attr-defined]
