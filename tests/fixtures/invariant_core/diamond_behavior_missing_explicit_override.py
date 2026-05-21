from __future__ import annotations

from typing import override

from tests.fixtures.invariant_core.diamond_runtime import BottomCategory
from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class MissingExplicitOverrideCategory(LocalCategoryBase):
    @override
    def super_categories(self) -> list[LocalCategoryBase]:
        return [BottomCategory.an_instance()]

    class ParentMethods:
        def right_method(self) -> int:
            return 5
