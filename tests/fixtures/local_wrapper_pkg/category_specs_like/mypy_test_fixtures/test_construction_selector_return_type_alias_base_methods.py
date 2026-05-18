"""Selector-owned construction return aliases inherit base methods."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase
from local_wrapper_pkg.category_specs_like.mypy_test_fixtures.construction_selector_return_alias_types import (
    _ConstructionBase,
    _DualObjects,
    _Subobjects,
)

if TYPE_CHECKING:
    from local_wrapper_pkg.category_specs_like.mypy_test_fixtures.construction_selector_return_alias_types import (
        SelectorDualModule,
        SelectorSubModule,
    )


class _Modules(LocalCategoryBase):
    Subobjects = _Subobjects

    def super_categories(self):  # type: ignore[override]
        return []

    class SubcategoryMethods:
        def DualObjects(self) -> LocalCategoryBase:
            return cast(LocalCategoryBase, _ConstructionBase.category_of(self))

    class ParentMethods:
        def tensor_power(self, exponent: int) -> object:
            return exponent

        def annihilator(self) -> object:
            return object()

        def dual(self) -> "SelectorDualModule":
            return _DualObjects.ParentMethods()

        def tensor_module(self) -> object:
            return self.dual().tensor_power(2)

    class ElementMethods:
        def parent(self) -> "_Modules.ParentMethods":
            return _Modules.ParentMethods()

        def span(self) -> "SelectorSubModule":
            return _Subobjects.ParentMethods()

        def inclusion(self) -> object:
            submodule = self.span()
            return submodule.Hom(self.parent())

        def annihilator(self) -> object:
            return self.span().annihilator()
