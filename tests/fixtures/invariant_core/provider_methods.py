from __future__ import annotations

from typing import Self

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class SelfReturnCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return []

    class ParentMethods:
        def normalized(self) -> Self:
            return self
