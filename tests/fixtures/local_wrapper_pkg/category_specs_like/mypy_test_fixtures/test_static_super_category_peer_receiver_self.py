"""Static super_categories() peer providers contribute receiver methods."""
from __future__ import annotations

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _FiniteProvider(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:  # type: ignore[override]
        return []

    class ParentMethods:
        def subposet(self, elements: object) -> object:
            return elements


class _MeetProvider(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:  # type: ignore[override]
        return []


class _FiniteMeetProvider(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:  # type: ignore[override]
        return [_MeetProvider(), _FiniteProvider()]

    class ParentMethods:
        def generated_substructure(self, elements: object) -> object:
            return self.subposet(elements)


def _fail_if_runtime_imported() -> None:
    raise AssertionError("runtime projection imported this fixture")


_fail_if_runtime_imported()
