"""Package-level category export for relative-import axiom fixtures."""
from __future__ import annotations

from typing import Any

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _ModuleParentMethods:
    def is_over_pid(self) -> bool:
        return False


class _Modules(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_Modules":
        return cls()

    ParentMethods = _ModuleParentMethods


Modules: Any = _Modules
