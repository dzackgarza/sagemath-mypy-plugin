"""Cross-module construction return aliases inherit base category methods."""
from __future__ import annotations

from typing import TYPE_CHECKING

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase
from local_wrapper_pkg.category_specs_like.mypy_test_fixtures.construction_return_alias_types import (
    _DualObjects,
)

if TYPE_CHECKING:
    from local_wrapper_pkg.category_specs_like.mypy_test_fixtures.construction_return_alias_types import (
        DualModule,
    )


class _Modules(LocalCategoryBase):
    DualObjects = _DualObjects

    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_Modules":
        return cls()

    class ParentMethods:
        def tensor_power(self, exponent: int) -> object:
            return exponent

        def dual(self) -> "DualModule":
            return _DualObjects.ParentMethods()

        def tensor_module(self) -> object:
            return self.dual().tensor_power(2)
