from __future__ import annotations

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.category import Category as _SageCategory  # type: ignore[import-untyped]


class LocalCategoryBase(_SageCategory):
    @classmethod
    def an_instance(cls) -> LocalCategoryBase:
        return cls()
