"""Missing explicit override fixture for real Sage category behavior test.

MissingExplicitOverrideCategory overrides order() from
FiniteGroupsOfOrderLessThanTwenty without the @override decorator.
With --enable-error-code=explicit-override enabled, mypy requires the
decorator when a method overrides an inherited method.

Behavior matrix:
  plugin off  → no error (parent provider invisible; method looks like a new definition)
  plugin on   → Method "order" is not using @override but is overriding [explicit-override]

This proves the plugin produces the provider MRO so that mypy can enforce
the explicit-override rule — a standard mypy rule, not plugin-specific logic.
"""

from __future__ import annotations

import sage.all  # type: ignore[import-untyped]  # noqa: F401
from sage.categories.category_singleton import Category_singleton  # type: ignore[import-untyped]

from tests.real_categories.finite_small_groups import FiniteGroupsOfOrderLessThanTwenty


class MissingExplicitOverrideCategory(Category_singleton):
    """Subcategory that overrides order() without the @override decorator."""

    def super_categories(self) -> list[object]:
        return [FiniteGroupsOfOrderLessThanTwenty()]

    class ParentMethods:
        def order(self) -> int:  # overrides parent but missing @override → [explicit-override]
            return 12
