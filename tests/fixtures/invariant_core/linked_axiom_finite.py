from __future__ import annotations

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.category_with_axiom import CategoryWithAxiom  # type: ignore[import-untyped]

from tests.fixtures.invariant_core.linked_axiom_root import LinkedAxiomRootCategory


class LinkedFiniteAxiomCategory(CategoryWithAxiom):
    _base_category_class_and_axiom = (LinkedAxiomRootCategory, "Finite")

    class ParentMethods:
        def linked_finite_axiom_parent(self) -> int:
            return 5
