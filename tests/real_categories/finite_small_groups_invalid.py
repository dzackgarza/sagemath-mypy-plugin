"""Invalid override fixtures for finite_small_groups behavior test.

InvalidMethodCategory attempts @override on a method that does not exist in
any parent provider class.  With plugin on this still fails (mypy standard
rule: no base method found).  With plugin off it also fails, but for the
wrong reason (provider MRO invisible).
"""

from __future__ import annotations

from typing import override

import sage.all  # type: ignore[import-untyped]  # noqa: F401
from sage.categories.category_singleton import Category_singleton  # type: ignore[import-untyped]

from tests.real_categories.finite_small_groups import FiniteGroupsOfOrderLessThanTwenty


class InvalidMethodCategory(Category_singleton):
    """Subcategory that incorrectly marks a non-existent method as @override."""

    def super_categories(self) -> list[object]:
        return [FiniteGroupsOfOrderLessThanTwenty()]

    class ParentMethods:
        @override
        def not_a_real_method(self) -> int:
            return 0
