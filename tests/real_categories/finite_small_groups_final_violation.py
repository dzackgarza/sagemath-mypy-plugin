"""Final violation fixture: attempts to override a @final method in KleinFourGroups.

KleinFourGroups.ParentMethods.is_klein_four_group() is decorated @final.
This fixture proves that the plugin correctly surfaces the @final violation
when a subcategory tries to override it.

  plugin off  → "no base method was found" (KleinFourGroups invisible to mypy)
  plugin on   → "Cannot override final attribute" (mypy standard @final check)
"""

from __future__ import annotations

from typing import override

import sage.all  # type: ignore[import-untyped]  # noqa: F401
from sage.categories.category import Category
from sage.categories.category_singleton import Category_singleton  # type: ignore[import-untyped]

from tests.real_categories.finite_small_groups import KleinFourGroups


class InvalidFinalOverrideCategory(Category_singleton):
    """Subcategory that illegally overrides a @final method from KleinFourGroups."""

    @override
    def super_categories(self) -> list[Category]:
        return [KleinFourGroups()]

    class ParentMethods:
        def is_klein_four_group(self) -> bool:  # should trigger @final violation
            return True
