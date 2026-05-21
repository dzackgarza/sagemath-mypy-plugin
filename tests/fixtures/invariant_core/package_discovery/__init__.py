from __future__ import annotations

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.category import Category  # type: ignore[import-untyped]
from sage.categories.category_with_axiom import CategoryWithAxiom  # type: ignore[import-untyped]
from sage.categories.category_with_axiom import CategoryWithAxiom_singleton  # type: ignore[import-untyped]
from sage.categories.objects import Objects  # type: ignore[import-untyped]

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class AbstractPackageCategory(LocalCategoryBase):
    pass


class UnboundAxiomPackageCategory(CategoryWithAxiom):
    pass


class UnboundSingletonAxiomPackageCategory(CategoryWithAxiom_singleton):
    def __init__(self, base_category: Category | None = None) -> None:
        assert base_category is not None
        super().__init__(base_category)


class ConcretePackageCategory(LocalCategoryBase):
    def super_categories(self) -> list[object]:
        return [Objects()]

    class ParentMethods:
        def concrete_package_method(self) -> int:
            return 1
