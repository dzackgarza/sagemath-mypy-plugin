"""Valid ElementMethods override in a local-wrapper hierarchy.

Exercises the ElementMethods container path through a local (non-sage.categories)
wrapper base.  The plugin must inject MRO bases for ElementMethods containers
the same way it does for ParentMethods.
"""
from typing import override as _override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class ElementMethods:
        def is_zero(self) -> bool:
            return False

        def norm(self) -> int:
            return 0


class _LocalSub(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_LocalBase.an_instance()]

    @classmethod
    def an_instance(cls) -> "_LocalSub":
        return cls()

    class ElementMethods:
        @_override
        def is_zero(self) -> bool:   # base defines this — must be valid
            return True

        @_override
        def norm(self) -> int:       # base defines this — must be valid
            return 1
