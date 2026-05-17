"""Static construction ownership supplies extra-super receiver methods."""
from collections.abc import Sequence
from typing import override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _ModuleParentMethods:
    def submodule(self, generators: Sequence[int]) -> object:
        return tuple(generators)

    def quotient_module(self, submodule: object, check: bool = True) -> object:
        return (submodule, check)


class _Quotients(LocalCategoryBase):
    def __init__(self, category: "_Modules") -> None:
        self._category = category

    def base_category(self) -> "_Modules":
        return self._category

    def extra_super_categories(self) -> list["_Modules"]:
        return [self.base_category()]

    def super_categories(self):  # type: ignore[override]
        return self.extra_super_categories()

    class ParentMethods:
        @override
        def quotient_module(self, submodule: object, check: bool = True) -> object:
            return (submodule, check)

        def quotient_by_generators(
            self,
            generators: Sequence[int],
            check: bool = True,
        ) -> object:
            return self.quotient_module(self.submodule(generators), check=check)


class _Modules(LocalCategoryBase):
    Quotients = _Quotients

    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_Modules":
        return cls()

    ParentMethods = _ModuleParentMethods


def _fail_if_runtime_imported() -> None:
    raise AssertionError("runtime projection imported this fixture")


_fail_if_runtime_imported()
