"""Assigned ParentMethods providers inherit methods from runtime Sage supercategories."""
from typing import override as _override

from sage.categories.posets import Posets as SagePosets

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _PosetParentMethods:
    @_override
    def le(self, x: object, y: object) -> bool:
        return x == y


class _LocalPosets(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [SagePosets()]

    @classmethod
    def an_instance(cls) -> "_LocalPosets":
        return cls()

    ParentMethods = _PosetParentMethods
