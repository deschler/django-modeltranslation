from __future__ import annotations

import sys
from typing import Literal, TypeVar

if sys.version_info >= (3, 11):
    from typing import Self, TypeAlias  # noqa: F401
else:
    from typing_extensions import Self, TypeAlias  # noqa: F401

AutoPopulate: TypeAlias = "bool | Literal['all', 'default', 'required']"

_K = TypeVar("_K")

# See https://github.com/typeddjango/django-stubs/blob/082955/django-stubs/utils/datastructures.pyi#L12-L14
_ListOrTuple: TypeAlias = "list[_K] | tuple[_K, ...]"
