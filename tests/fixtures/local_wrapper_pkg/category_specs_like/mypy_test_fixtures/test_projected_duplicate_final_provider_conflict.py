"""Projected method-container bases with duplicate final names should compose."""
from __future__ import annotations

from typing import final

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _FirstCategory(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_FirstCategory":
        return cls()

    class ParentMethods:
        @final
        def common(self) -> int:
            return 1

        def left(self) -> int:
            return 2


class _SecondCategory(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_SecondCategory":
        return cls()

    class ParentMethods:
        @final
        def common(self) -> int:
            return 3

        def right(self) -> int:
            return 4


class _CombinedCategory(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_FirstCategory.an_instance(), _SecondCategory.an_instance()]

    @classmethod
    def an_instance(cls) -> "_CombinedCategory":
        return cls()

    class ParentMethods:
        def uses_right(self) -> int:
            return self.right()
