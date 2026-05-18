"""Axiom base categories expose selectors inherited from their semantic base."""
from __future__ import annotations

from collections.abc import Sequence
from typing import final

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase
from sage.categories.category import Category


class _RootCategory(LocalCategoryBase):
    class SubcategoryMethods:
        @final
        def RootSelector(self) -> Category:
            return self._with_axiom("RootSelector")


class _AxiomCategory(LocalCategoryBase):
    _base_category_class_and_axiom = (_RootCategory, "Axiom")


class _NestedAxiomCategory(LocalCategoryBase):
    _base_category_class_and_axiom = (_AxiomCategory, "NestedAxiom")

    def extra_super_categories(self) -> Sequence[Category]:
        return [self.base_category().RootSelector()]
