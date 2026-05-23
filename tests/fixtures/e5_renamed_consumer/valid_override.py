"""Valid @override fixture for the renamed-consumer package.

ValidRenamedConsumer subcategories RenamedRootGroupCategory and overrides
cardinality() correctly.  With plugin on, this should produce no errors.
With plugin off, mypy cannot see RenamedRootGroupCategory.ParentMethods as
a base, so @override finds no base method — "no base method was found".
"""

from __future__ import annotations

from typing import Literal, override

import sage.all  # type: ignore[import-untyped]  # noqa: F401
from sage.categories.category import Category
from sage.categories.category_singleton import Category_singleton  # type: ignore[import-untyped]

from tests.fixtures.e5_renamed_consumer.categories import RenamedRootGroupCategory


class ValidRenamedConsumer(Category_singleton):
    """Valid subcategory: overrides cardinality() with a subtype return type."""

    @override
    def super_categories(self) -> list[Category]:
        return [RenamedRootGroupCategory()]

    class ParentMethods:
        @override
        def cardinality(self) -> Literal[12]:
            return 12
