"""Valid ElementMethods @override in a local-wrapper hierarchy."""
from typing import override as _override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class ElementMethods:
        def is_zero(self) -> bool:
            return False

        def norm(self) -> int:
            return 0


class _LocalSub(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_LocalBase.an_instance()]

    @classmethod
    def an_instance(cls) -> "_LocalSub":
        return cls()

    class ElementMethods:
        @_override
        def is_zero(self) -> bool:
            return True

        @_override
        def norm(self) -> int:
            return 1
