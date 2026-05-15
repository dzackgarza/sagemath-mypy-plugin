"""@final on method container assignment in a local-wrapper hierarchy.

A category's ParentMethods defines a @final method. A subcategory assigns
ParentMethods to a helper class that also uses @final. The plugin must
propagate @final semantics through the alias so that mypy correctly
treats the method as final (and rejects overrides).
"""
from typing import final, override as _override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class ParentMethods:
        @final
        def of(self) -> int:
            return 0


class _FinalHelper:
    @final
    def of(self) -> int:
        return 1


class _LocalSub(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_LocalBase.an_instance()]

    @classmethod
    def an_instance(cls) -> "_LocalSub":
        return cls()

    ParentMethods = _FinalHelper
