from __future__ import annotations

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.category_with_axiom import CategoryWithAxiom  # type: ignore[import-untyped]
from sage.categories.sets_cat import Sets  # type: ignore[import-untyped]

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class AxiomRootCategory(LocalCategoryBase):
    def super_categories(self) -> list[object]:
        return [Sets()]

    class ParentMethods:
        def root_axiom_parent(self) -> int:
            return 1

    class Finite(CategoryWithAxiom):
        class ParentMethods:
            def finite_axiom_parent(self) -> int:
                return 2
