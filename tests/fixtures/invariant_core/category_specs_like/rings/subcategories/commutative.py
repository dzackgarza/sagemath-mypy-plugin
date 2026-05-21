from __future__ import annotations

from tests.fixtures.invariant_core.category_specs_like.cat import Category
from tests.fixtures.invariant_core.category_specs_like.rings import Rings


class _CommutativeRings(Category):
    _base_category_class_and_axiom = (Rings, "Commutative")

    def super_categories(self) -> list[Category]:
        return [Rings.an_instance()]

    class ParentMethods:
        def is_commutative_ring(self) -> bool:
            return True
