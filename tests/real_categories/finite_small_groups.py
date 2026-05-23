"""Real Sage category fixtures: finite groups of small order.

These are honest mathematical categories that subclass real Sage category
instances.  They exercise Sage's _make_named_class dynamic provider
construction and produce a genuine runtime MRO for the plugin to project.

Phase 3 proof target: for each category, the Sage oracle records the real
runtime named-class MRO, and the plugin sets mypy TypeInfo.bases/mro to
that projected provider graph.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Literal, cast, final, override

import sage.all  # type: ignore[import-untyped]  # noqa: F401
from sage.categories.category import Category
from sage.categories.category_singleton import Category_singleton  # type: ignore[import-untyped]
from sage.categories.groups import Groups  # type: ignore[import-untyped]


class FiniteGroupsOfOrderLessThanTwenty(Category_singleton):
    """Category of finite groups whose order is at most 20."""

    @override
    def super_categories(self) -> list[Category]:
        return [cast(Category, Groups().Finite())]  # type: ignore[attr-defined]

    class ParentMethods:
        @abstractmethod
        def order(self) -> int: ...

        def has_even_order(self) -> bool:
            return self.order() % 2 == 0  # type: ignore[attr-defined]


class EvenOrderGroupsOfOrderLessThanTwenty(Category_singleton):
    """Category of finite groups of even order at most 20."""

    @override
    def super_categories(self) -> list[Category]:
        return [FiniteGroupsOfOrderLessThanTwenty()]

    class ParentMethods:
        @override
        @abstractmethod
        def has_even_order(self) -> Literal[True]: ...

        @abstractmethod
        def has_element_of_order_two(self) -> bool: ...


class GroupsOfOrderFour(Category_singleton):
    """Category of groups of order exactly 4."""

    @override
    def super_categories(self) -> list[Category]:
        return [EvenOrderGroupsOfOrderLessThanTwenty()]

    class ParentMethods:
        @override
        def order(self) -> Literal[4]:
            return 4

        @abstractmethod
        def is_klein_four_group(self) -> bool: ...


class KleinFourGroups(Category_singleton):
    """Category of groups isomorphic to the Klein four-group."""

    @override
    def super_categories(self) -> list[Category]:
        return [GroupsOfOrderFour()]

    class ParentMethods:
        @override
        @final
        def is_klein_four_group(self) -> Literal[True]:
            return True
