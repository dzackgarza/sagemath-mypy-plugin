from __future__ import annotations

from tests.fixtures.invariant_core.category_specs_like.cat import (
    Category,
    Category_singleton,
)


class _RingObjectMethods:
    def is_commutative_ring(self) -> bool:
        return False


class Rings(Category_singleton):
    def super_categories(self) -> list[Category]:
        return []

    ParentMethods = _RingObjectMethods
