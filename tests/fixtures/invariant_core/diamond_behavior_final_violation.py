from __future__ import annotations

from typing import final, override

from tests.fixtures.invariant_core.diamond_runtime import BottomCategory
from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class FinalBaseCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [BottomCategory.an_instance()]

    class ParentMethods:
        @final
        def final_method(self) -> int:
            return 5


class FinalViolationCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [FinalBaseCategory.an_instance()]

    class ParentMethods:
        @override
        def final_method(self) -> int:
            return 6
