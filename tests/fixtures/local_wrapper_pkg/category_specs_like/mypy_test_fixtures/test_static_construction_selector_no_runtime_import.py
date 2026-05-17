"""Static construction selector detection must not execute this module."""
from __future__ import annotations

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _StaticConstruction:
    def __init__(self, category: "_RuntimeHostileSelectorCategory") -> None:
        self._category = category

    def super_categories(self) -> list[object]:
        return []

    @classmethod
    def an_instance(cls) -> "_StaticConstruction":
        return cls(_RuntimeHostileSelectorCategory.an_instance())


class _RuntimeHostileSelectorCategory(LocalCategoryBase):
    HostileConstruction = _StaticConstruction

    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_RuntimeHostileSelectorCategory":
        return cls()


def hostile_selector() -> _StaticConstruction:
    return _RuntimeHostileSelectorCategory.an_instance().HostileConstruction()


def _fail_if_runtime_imported() -> None:
    raise AssertionError("mypy plugin executed a fixture module during classification")


_fail_if_runtime_imported()
