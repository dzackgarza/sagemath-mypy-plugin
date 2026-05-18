from __future__ import annotations

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.sets_cat import Sets  # type: ignore[import-untyped]
from sage.misc.lazy_import import LazyImport  # type: ignore[import-untyped]

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class LinkedAxiomRootCategory(LocalCategoryBase):
    def super_categories(self) -> list[object]:
        return [Sets()]

    class ParentMethods:
        def linked_root_parent(self) -> int:
            return 4


LinkedAxiomRootCategory.Finite = LazyImport(
    "tests.fixtures.invariant_core.linked_axiom_finite",
    "LinkedFiniteAxiomCategory",
    as_name="Finite",
)
