from __future__ import annotations

from typing import override

from sage.categories.category import Category

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase
from tests.fixtures.invariant_core.provider_roles.diamond import BottomCategory


class ValidElementOverrideCategory(LocalCategoryBase):
    @override
    def super_categories(self) -> list[Category]:
        return [BottomCategory.an_instance()]

    class ElementMethods:
        @override
        def bottom_element(self) -> int:
            return 4
