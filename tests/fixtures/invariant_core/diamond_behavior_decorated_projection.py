from __future__ import annotations

from tests.fixtures.invariant_core.diamond_behavior_decorated_base import (
    DecoratedBaseCategory,
)
from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class DecoratedProjectionCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [DecoratedBaseCategory.an_instance()]

    class ParentMethods:
        def decorated_projection_probe(self) -> int:
            return 99
