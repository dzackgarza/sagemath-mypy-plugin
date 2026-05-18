from __future__ import annotations

from typing import override

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase
from tests.fixtures.invariant_core.provider_roles.diamond import BottomCategory


class ValidSubcategoryOverrideCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [BottomCategory.an_instance()]

    class SubcategoryMethods:
        @override
        def bottom_subcategory(self) -> int:
            return 40
