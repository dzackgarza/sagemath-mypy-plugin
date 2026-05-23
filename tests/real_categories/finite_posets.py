"""Real Sage category fixtures: finite posets.

These are unrelated to the finite_small_groups.py chain but intentionally share
method names with those categories (order(), has_even_order()).  This is the
Phase 3 P5 proof fixture: if the plugin used name-based matching rather than
MRO-based projection, it would confuse methods across the two chains.

The test asserts that @override resolves correctly in BOTH chains independently,
proving the plugin keys projections on the Sage runtime MRO graph, not on
method names.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Literal, cast, override

import sage.all  # type: ignore[import-untyped]  # noqa: F401
from sage.categories.category import Category
from sage.categories.category_singleton import Category_singleton  # type: ignore[import-untyped]
from sage.categories.finite_sets import FiniteSets  # type: ignore[import-untyped]


class FinitePosets(Category_singleton):
    """Category of finite partially ordered sets.

    Completely unrelated to the Groups hierarchy in finite_small_groups.py,
    but intentionally uses the same method name 'order' (= size of the poset).
    """

    @override
    def super_categories(self) -> list[Category]:
        return [cast(Category, FiniteSets())]

    class ParentMethods:
        @abstractmethod
        def order(self) -> int: ...

        def has_even_order(self) -> bool:
            return self.order() % 2 == 0  # type: ignore[attr-defined]


class SmallFinitePosets(Category_singleton):
    """Category of finite posets of small size (order ≤ 10)."""

    @override
    def super_categories(self) -> list[Category]:
        return [FinitePosets()]

    class ParentMethods:
        @override
        def order(self) -> Literal[10]:
            return 10

        @override
        def has_even_order(self) -> Literal[True]:
            return True
