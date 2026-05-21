"""Phase 7 E5: renamed-consumer fixture.

This package intentionally lives in a namespace completely unrelated to
'category_specs', 'tests.fixtures.invariant_core', or 'tests.real_categories'.
The plugin must discover and project its categories from config alone.

Category chain:
  RenamedRootGroupCategory — subclasses Groups().Finite(), defines cardinality()
  RenamedSmallGroupCategory — subcategory, overrides cardinality() -> Literal[6]

Both classes are real Sage Category_singleton subclasses with super_categories()
returning real Sage category objects.  They are not mocks or stubs.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Literal, override

import sage.all  # type: ignore[import-untyped]  # noqa: F401
from sage.categories.category_singleton import Category_singleton  # type: ignore[import-untyped]
from sage.categories.groups import Groups  # type: ignore[import-untyped]


class RenamedRootGroupCategory(Category_singleton):
    """Category of finite groups with a cardinality method.

    Subclasses Groups().Finite() — a real Sage axiom category constructed
    at runtime.  The plugin must project its parent_class MRO correctly
    to make @override on cardinality() visible to mypy.
    """

    def super_categories(self) -> list[object]:
        return [Groups().Finite()]  # type: ignore[attr-defined]

    class ParentMethods:
        @abstractmethod
        def cardinality(self) -> int: ...


class RenamedSmallGroupCategory(Category_singleton):
    """Category of small finite groups whose cardinality is 6."""

    def super_categories(self) -> list[object]:
        return [RenamedRootGroupCategory()]

    class ParentMethods:
        @override
        def cardinality(self) -> Literal[6]:
            return 6
