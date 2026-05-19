"""Signature mismatch fixture for real Sage category behavior test.

SignatureMismatchCategory overrides has_even_order() from
FiniteGroupsOfOrderLessThanTwenty but narrows the return type to str,
which is not a subtype of bool.

Behavior matrix:
  plugin off  → "no base method was found" (parent provider invisible to mypy)
  plugin on   → Signature of "has_even_order" incompatible with supertype [override]

This proves the plugin delegates override-signature checking entirely to mypy's
standard inheritance machinery — no plugin-specific error filtering.
"""

from __future__ import annotations

from typing import override

import sage.all  # type: ignore[import-untyped]  # noqa: F401
from sage.categories.category_singleton import Category_singleton  # type: ignore[import-untyped]

from tests.real_categories.finite_small_groups import FiniteGroupsOfOrderLessThanTwenty


class SignatureMismatchCategory(Category_singleton):
    """Subcategory that overrides has_even_order() with an incompatible return type."""

    def super_categories(self) -> list[object]:
        return [FiniteGroupsOfOrderLessThanTwenty()]

    class ParentMethods:
        @override
        def has_even_order(self) -> str:  # str is not a subtype of bool → [override]
            return "yes"
