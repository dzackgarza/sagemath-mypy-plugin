from __future__ import annotations

from typing import override

from tests.fixtures.invariant_core.diamond_behavior_decorated_base import (
    DecoratedBaseCategory,
)
from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class DecoratedProjectionCategory(LocalCategoryBase):
    @override
    def super_categories(self) -> list[LocalCategoryBase]:
        return [DecoratedBaseCategory.an_instance()]

    class ParentMethods:
        def decorated_projection_probe(self) -> int:
            return 99
