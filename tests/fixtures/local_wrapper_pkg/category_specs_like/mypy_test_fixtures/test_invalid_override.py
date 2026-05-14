"""Invalid override in a local-wrapper hierarchy.

The sub-category uses @override on a method that does not exist in any base
container.  Mypy must report "no base method was found" (nonzero exit code).
This guards against the plugin silently passing everything by returning None
from projection — a silent no-op would make this fixture incorrectly green.
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


class _LocalSub(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_LocalBase.an_instance()]

    @classmethod
    def an_instance(cls) -> "_LocalSub":
        return cls()

    class ParentMethods:
        @_override
        def nonexistent_method(self) -> int:  # no base defines this — must be an error
            return 99
