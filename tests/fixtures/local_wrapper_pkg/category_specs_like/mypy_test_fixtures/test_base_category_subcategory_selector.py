"""Axiom categories should retain the declared base category selector surface."""
from __future__ import annotations

from collections.abc import Sequence
from typing import final

from sage.categories.category import Category
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _BaseCategory(LocalCategoryBase):
    class SubcategoryMethods:
        @final
        def Special(self) -> object:
            return self._with_axiom("Special")


class _AxiomCategory(LocalCategoryBase):
    _base_category_class_and_axiom = (_BaseCategory, "Axiom")

    def extra_super_categories(self) -> Sequence[Category]:
        return [self.base_category().Special()]
