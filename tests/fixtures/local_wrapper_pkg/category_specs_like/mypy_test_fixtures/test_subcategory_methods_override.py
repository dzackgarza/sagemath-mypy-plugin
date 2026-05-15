"""Valid SubcategoryMethods override in a local-wrapper hierarchy.

Exercises the SubcategoryMethods container path through a local (non-sage.categories)
wrapper base.  The plugin must inject MRO bases for SubcategoryMethods containers
the same way it does for ParentMethods and ElementMethods.
"""
from typing import override as _override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class SubcategoryMethods:
        def axiom_label(self) -> str:
            return "base"

        def extra_super_categories(self) -> list:
            return []


class _LocalSub(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_LocalBase.an_instance()]

    @classmethod
    def an_instance(cls) -> "_LocalSub":
        return cls()

    class SubcategoryMethods:
        @_override
        def axiom_label(self) -> str:   # base defines this — must be valid
            return "sub"

        @_override
        def extra_super_categories(self) -> list:  # base defines this — must be valid
            return []
