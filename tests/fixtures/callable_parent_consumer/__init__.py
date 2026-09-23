"""Consumer package that exports a callable parent next to its category.

A research session module binds ready-made parents (a field, a ring) at module
level. A Sage parent is callable, because calling it constructs an element, and
its class is a Cython extension type, so `inspect.signature` cannot read it.
Category discovery must still find the category defined here.
"""

from __future__ import annotations

import sage.all  # type: ignore[import-untyped]  # noqa: F401
from sage.categories.category_singleton import Category_singleton  # type: ignore[import-untyped]
from sage.categories.sets_cat import Sets  # type: ignore[import-untyped]
from sage.structure.parent import Parent  # type: ignore[import-untyped]
from sage.structure.unique_representation import UniqueRepresentation  # type: ignore[import-untyped]


class PointedSets(Category_singleton):
    """Sets with a chosen base point."""

    def super_categories(self) -> list[object]:
        return [Sets()]

    class ParentMethods:
        def base_point(self) -> object:
            return self.an_element()  # type: ignore[attr-defined]


class TwoPointSet(UniqueRepresentation, Parent):
    """A two-element pointed set."""

    def __init__(self) -> None:
        Parent.__init__(self, category=PointedSets())


TWO_POINTS = TwoPointSet()
