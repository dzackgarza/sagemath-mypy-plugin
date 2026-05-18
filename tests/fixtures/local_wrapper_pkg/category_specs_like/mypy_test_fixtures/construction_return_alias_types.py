"""Type aliases for construction-category ParentMethods return types."""
from __future__ import annotations

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _DualObjects(LocalCategoryBase):
    def __init__(self, category: LocalCategoryBase) -> None:
        self._category = category

    def base_category(self) -> LocalCategoryBase:
        return self._category

    def extra_super_categories(self) -> list[LocalCategoryBase]:
        return [self.base_category()]

    def super_categories(self):  # type: ignore[override]
        return self.extra_super_categories()

    class ParentMethods: ...


DualModule = _DualObjects.ParentMethods
