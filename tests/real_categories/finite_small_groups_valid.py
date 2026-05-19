"""Valid override fixtures for finite_small_groups behavior test.

EvenOrderSubcategoryVariant subclasses FiniteGroupsOfOrderLessThanTwenty and
provides a valid override of has_even_order() (covariant return type).

With plugin on: @override resolves because the plugin projects
  EvenOrderSubcategoryVariant.ParentMethods bases →
  (FiniteGroupsOfOrderLessThanTwenty.ParentMethods,)
  which contains has_even_order().

With plugin off: mypy cannot see FiniteGroupsOfOrderLessThanTwenty.ParentMethods
  as a base and reports "no base method was found".
"""

from __future__ import annotations

from typing import Literal, override

import sage.all  # type: ignore[import-untyped]  # noqa: F401
from sage.categories.category_singleton import Category_singleton  # type: ignore[import-untyped]

from tests.real_categories.finite_small_groups import FiniteGroupsOfOrderLessThanTwenty


class ValidHasEvenOrderCategory(Category_singleton):
    """Subcategory of groups of even order < 20; provides a valid override."""

    def super_categories(self) -> list[object]:
        return [FiniteGroupsOfOrderLessThanTwenty()]

    class ParentMethods:
        @override
        def has_even_order(self) -> Literal[True]:
            return True
