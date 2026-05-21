from __future__ import annotations

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class TopCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return []

    class ParentMethods:
        def top_method(self) -> int:
            return 1


class LeftCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [TopCategory.an_instance()]

    class ParentMethods:
        def left_method(self) -> int:
            return 2


class RightCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [TopCategory.an_instance()]

    class ParentMethods:
        def right_method(self) -> int:
            return 3


class BottomCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [LeftCategory.an_instance(), RightCategory.an_instance()]

    class ParentMethods:
        def bottom_method(self) -> int:
            return 4
