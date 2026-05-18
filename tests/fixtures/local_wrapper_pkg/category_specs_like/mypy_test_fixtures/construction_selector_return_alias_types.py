"""Type aliases for selector-owned construction ParentMethods."""
from __future__ import annotations

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _ConstructionBase(LocalCategoryBase):
    @classmethod
    def category_of(cls, category: object) -> LocalCategoryBase:
        return cls()


class _DualObjects(_ConstructionBase):
    def __init__(self, category: LocalCategoryBase) -> None:
        self._category = category

    def base_category(self) -> LocalCategoryBase:
        return self._category

    def extra_super_categories(self) -> list[LocalCategoryBase]:
        return [self.base_category()]

    def super_categories(self):  # type: ignore[override]
        return self.extra_super_categories()

    class ParentMethods: ...


class _Subobjects(_ConstructionBase):
    def as_subobject_of_self(self, category: object) -> "_Subobjects.ParentMethods":
        return self.ParentMethods()

    class ParentMethods: ...


SelectorDualModule = _DualObjects.ParentMethods
SelectorSubModule = _Subobjects.ParentMethods
