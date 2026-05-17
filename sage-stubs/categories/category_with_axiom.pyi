from typing import Any

from .category import Category


class CategoryWithAxiom(Category):
    def ambient_category(self) -> Category: ...
    def defining_predicates(self) -> tuple[str, ...]: ...
    def defining_predicate(self, candidate: Any) -> bool: ...


class CategoryWithAxiom_over_base_ring(CategoryWithAxiom): ...


class CategoryWithAxiom_singleton(CategoryWithAxiom): ...


all_axioms: tuple[str, ...]
