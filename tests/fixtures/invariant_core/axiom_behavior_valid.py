from __future__ import annotations

from typing import override

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.category import Category
from sage.categories.category_with_axiom import CategoryWithAxiom  # type: ignore[import-untyped]

from tests.fixtures.invariant_core.axioms import AxiomRootCategory
from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class ValidAxiomOverrideCategory(LocalCategoryBase):
    @override
    def super_categories(self) -> list[Category]:
        return [AxiomRootCategory.an_instance()]

    class Finite(CategoryWithAxiom):
        class ParentMethods:
            @override
            def finite_axiom_parent(self) -> int:
                return 3
