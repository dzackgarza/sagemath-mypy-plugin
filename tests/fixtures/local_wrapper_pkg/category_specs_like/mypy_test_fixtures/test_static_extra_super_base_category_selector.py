"""Static fallback should resolve base_category() axiom selectors."""
from __future__ import annotations

from typing import override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _RootCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:  # type: ignore[override]
        return []

    class SubcategoryMethods:
        def Generated(self) -> LocalCategoryBase:
            raise NotImplementedError


class _GeneratedProvider(LocalCategoryBase):
    _base_category_class_and_axiom = (_RootCategory, "Generated")

    def super_categories(self) -> list[LocalCategoryBase]:  # type: ignore[override]
        return []

    class ParentMethods:
        def provided_by_base_category_selector(self) -> int:
            return 1


class _AxiomCategory(LocalCategoryBase):
    _base_category_class_and_axiom = (_RootCategory, "Axiom")

    def extra_super_categories(self) -> list[LocalCategoryBase]:
        return [self.base_category().Generated()]

    class ParentMethods:
        @override
        def provided_by_base_category_selector(self) -> int:
            return 2


def _fail_if_runtime_imported() -> None:
    raise AssertionError("runtime projection imported this fixture")


_fail_if_runtime_imported()
