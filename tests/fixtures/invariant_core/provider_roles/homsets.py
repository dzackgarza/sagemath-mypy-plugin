from __future__ import annotations

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.homsets import HomsetsCategory  # type: ignore[import-untyped]
from sage.categories.objects import Objects  # type: ignore[import-untyped]

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class TopCategory(LocalCategoryBase):
    def super_categories(self) -> list[object]:
        return [Objects()]

    class Homsets(HomsetsCategory):
        def extra_super_categories(self) -> list[object]:
            return []

        class ParentMethods:
            def top_homset_parent(self) -> int:
                return 1

        class ElementMethods:
            def top_homset_element(self) -> int:
                return 10


class BottomCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [TopCategory.an_instance()]

    def is_full_subcategory(self, category: object) -> bool:
        return category is TopCategory.an_instance()

    class Homsets(HomsetsCategory):
        def extra_super_categories(self) -> list[object]:
            return []

        class ParentMethods:
            def bottom_homset_parent(self) -> int:
                return 2

        class ElementMethods:
            def bottom_homset_element(self) -> int:
                return 20
