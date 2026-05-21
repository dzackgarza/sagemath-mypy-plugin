from __future__ import annotations

from tests.fixtures.invariant_core.category_specs_like.cat import Category
from tests.fixtures.invariant_core.category_specs_like.rings import Rings


class _NamespaceCommutativeRings(Category):
    def super_categories(self) -> list[Category]:
        return [Rings.an_instance()]

    class ParentMethods:
        def namespace_commutative_ring(self) -> bool:
            return True


class _BaseDependentConstruction(Category):
    def __init__(self, base_category: Category) -> None:
        self._base_category = base_category

    def super_categories(self) -> list[Category]:
        return [self._base_category]

    class ParentMethods:
        def base_dependent_method(self) -> bool:
            return True
