"""Static fallback should read extra_super_categories() provider containers."""
from __future__ import annotations

from typing import override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _RootCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:  # type: ignore[override]
        return []


class _ExtraProvider(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_ExtraProvider":
        return cls()

    class ParentMethods:
        def provided_by_extra_super(self) -> int:
            return 1


class _AxiomCategory(LocalCategoryBase):
    _base_category_class_and_axiom = (_RootCategory, "Axiom")

    def extra_super_categories(self) -> list[_ExtraProvider]:
        return [_ExtraProvider.an_instance()]

    class ParentMethods:
        @override
        def provided_by_extra_super(self) -> int:
            return 2


def _fail_if_runtime_imported() -> None:
    raise AssertionError("runtime projection imported this fixture")


_fail_if_runtime_imported()
