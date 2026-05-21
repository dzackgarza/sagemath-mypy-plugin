from __future__ import annotations

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.objects import Objects  # type: ignore[import-untyped]

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class SharedParentMethods:
    def shared_parent_method(self) -> int:
        return 1


class SharedProviderTopCategory(LocalCategoryBase):
    def super_categories(self) -> list[object]:
        return [Objects()]

    ParentMethods = SharedParentMethods


class SharedProviderBottomCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [SharedProviderTopCategory.an_instance()]

    ParentMethods = SharedParentMethods
