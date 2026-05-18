"""ParentMethods may override methods supplied by concrete receiver classes."""
from __future__ import annotations

from typing import override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _RuntimeFreeModuleReceiverMethods:
    def basis(self) -> object:
        return object()

    def bases(self) -> list[object]:
        return [self.basis()]

    def dimension(self) -> object:
        return object()


class _RuntimeFreeModule(_RuntimeFreeModuleReceiverMethods): ...


class _FreeFiniteRank(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_FreeFiniteRank":
        return cls()

    class ParentMethods:
        @override
        def bases(self) -> list[object]:
            if isinstance(self, _RuntimeFreeModule):
                return _RuntimeFreeModule.bases(self)
            return [self.basis()]

        @override
        def dimension(self) -> object:
            if isinstance(self, _RuntimeFreeModule):
                return _RuntimeFreeModule.dimension(self)
            return object()
