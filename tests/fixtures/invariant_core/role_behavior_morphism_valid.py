from __future__ import annotations

from typing import override

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase
from tests.fixtures.invariant_core.provider_roles.diamond import BottomCategory


class ValidMorphismOverrideCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [BottomCategory.an_instance()]

    class MorphismMethods:
        @override
        def bottom_morphism(self) -> int:
            return 400
