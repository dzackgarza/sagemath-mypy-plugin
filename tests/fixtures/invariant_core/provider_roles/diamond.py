from __future__ import annotations

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class TopCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return []

    class ElementMethods:
        def top_element(self) -> int:
            return 1

    class SubcategoryMethods:
        def top_subcategory(self) -> int:
            return 10


class LeftCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [TopCategory.an_instance()]

    class ElementMethods:
        def left_element(self) -> int:
            return 2

    class SubcategoryMethods:
        def left_subcategory(self) -> int:
            return 20


class RightCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [TopCategory.an_instance()]

    class ElementMethods:
        def right_element(self) -> int:
            return 3

    class SubcategoryMethods:
        def right_subcategory(self) -> int:
            return 30


class BottomCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [LeftCategory.an_instance(), RightCategory.an_instance()]

    class ElementMethods:
        def bottom_element(self) -> int:
            return 4

    class SubcategoryMethods:
        def bottom_subcategory(self) -> int:
            return 40
