"""Runtime construction classification failures must remain ordinary diagnostics."""
from __future__ import annotations

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _OpaqueConstruction:
    def __init__(self, category: "_RuntimeHostileOpaqueCategory") -> None:
        self._category = category

    @classmethod
    def an_instance(cls) -> "_OpaqueConstruction":
        return cls(_RuntimeHostileOpaqueCategory.an_instance())


class _RuntimeHostileOpaqueCategory(LocalCategoryBase):
    OpaqueConstruction = _OpaqueConstruction

    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_RuntimeHostileOpaqueCategory":
        return cls()


def opaque_selector() -> _OpaqueConstruction:
    return _RuntimeHostileOpaqueCategory.an_instance().OpaqueConstruction()


def _fail_if_runtime_imported() -> None:
    raise AssertionError("runtime category classification imported this fixture")


_fail_if_runtime_imported()
