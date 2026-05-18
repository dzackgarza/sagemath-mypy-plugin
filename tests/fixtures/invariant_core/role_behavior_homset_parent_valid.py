from __future__ import annotations

from typing import override

from sage.categories.homsets import HomsetsCategory  # type: ignore[import-untyped]

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase
from tests.fixtures.invariant_core.provider_roles.homsets import BottomCategory


class ValidHomsetParentOverrideCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [BottomCategory.an_instance()]

    def is_full_subcategory(self, category: object) -> bool:
        return category is BottomCategory.an_instance()

    class Homsets(HomsetsCategory):
        def extra_super_categories(self) -> list[object]:
            return []

        class ParentMethods:
            @override
            def bottom_homset_parent(self) -> int:
                return 3
