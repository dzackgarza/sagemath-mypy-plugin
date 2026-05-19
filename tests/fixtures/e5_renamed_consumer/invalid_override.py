"""Invalid @override fixture for the renamed-consumer package.

InvalidRenamedConsumer subcategories RenamedRootGroupCategory and tries to
@override a method that does not exist in the parent provider chain.
With plugin on, mypy still reports "no base method was found" because the
method name is genuinely not defined in any projected provider class.
"""

from __future__ import annotations

from typing import override

import sage.all  # type: ignore[import-untyped]  # noqa: F401
from sage.categories.category_singleton import Category_singleton  # type: ignore[import-untyped]

from tests.fixtures.e5_renamed_consumer.categories import RenamedRootGroupCategory


class InvalidRenamedConsumer(Category_singleton):
    """Invalid subcategory: @override on a method that has no base definition."""

    def super_categories(self) -> list[object]:
        return [RenamedRootGroupCategory()]

    class ParentMethods:
        @override
        def nonexistent_renamed_method(self) -> int:  # no base method → error
            return 0
