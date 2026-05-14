"""Valid override in a local-wrapper hierarchy.

The base category is NOT a direct subclass of sage.categories.category.Category —
it inherits through a local wrapper (mirroring category_specs).  The plugin must
still inject the correct MRO bases so that @override resolves correctly and mypy
reports exit code 0.
"""
from typing import override as _override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class ParentMethods:
        def compute(self) -> int:
            return 0

        def is_finite(self) -> bool:
            return True


class _LocalSub(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_LocalBase.an_instance()]

    @classmethod
    def an_instance(cls) -> "_LocalSub":
        return cls()

    class ParentMethods:
        @_override
        def compute(self) -> int:   # base defines this — must be valid
            return 1

        @_override
        def is_finite(self) -> bool:  # base defines this — must be valid
            return False
