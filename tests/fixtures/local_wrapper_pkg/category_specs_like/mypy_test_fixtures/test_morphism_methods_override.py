"""Valid MorphismMethods override in a local-wrapper hierarchy.

Exercises the MorphismMethods container path through a local (non-sage.categories)
wrapper base.  The plugin must inject MRO bases for MorphismMethods containers
the same way it does for ParentMethods, ElementMethods, and SubcategoryMethods.
"""
from typing import override as _override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class MorphismMethods:
        def on_generators(self) -> str:
            return "base"

        def is_injective(self) -> bool:
            return False


class _LocalSub(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_LocalBase.an_instance()]

    @classmethod
    def an_instance(cls) -> "_LocalSub":
        return cls()

    class MorphismMethods:
        @_override
        def on_generators(self) -> str:   # base defines this — must be valid
            return "sub"

        @_override
        def is_injective(self) -> bool:   # base defines this — must be valid
            return True
