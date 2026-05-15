"""Invalid helper-alias @override — the helper uses @override on a method
with no base definition in any ancestor container.
"""
from typing import override as _override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class ParentMethods:
        def compute(self) -> int:
            return 0


class _BadParentMethods:
    @_override
    def compute(self) -> int:  # Valid — base defines compute
        return 1

    @_override
    def nonexistent_method(self) -> int:  # INVALID — no base defines this
        return 99


class _LocalSub(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_LocalBase.an_instance()]

    @classmethod
    def an_instance(cls) -> "_LocalSub":
        return cls()

    ParentMethods = _BadParentMethods
