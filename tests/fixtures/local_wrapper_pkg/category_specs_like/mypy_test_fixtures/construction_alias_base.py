"""Shared base category whose ParentMethods provider is a top-level alias."""
from collections.abc import Sequence

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase
from sage.misc.lazy_import import LazyImport


class _ModuleParentMethods:
    def submodule(self, generators: Sequence[int]) -> object:
        return tuple(generators)

    def quotient_module(self, submodule: object) -> object:
        return submodule


class _Modules(LocalCategoryBase):
    Quotients = LazyImport(
        "local_wrapper_pkg.category_specs_like.mypy_test_fixtures."
        "test_cross_module_construction_alias_provider",
        "_Quotients",
    )

    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_Modules":
        return cls()

    ParentMethods = _ModuleParentMethods
