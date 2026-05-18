"""ParentMethods may override methods supplied by imported Sage receiver classes."""
from __future__ import annotations

from typing import override

from sage.modules.free_module import (
    FreeModule_generic as SageFreeModuleGeneric,
)
from sage.tensor.modules.finite_rank_free_module import (
    FiniteRankFreeModule as SageFiniteRankFreeModule,
)

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _FreeFiniteRank(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_FreeFiniteRank":
        return cls()

    class ParentMethods:
        def basis(self) -> object: ...

        def rank(self) -> object: ...

        @override
        def bases(self) -> list[object]:
            if isinstance(self, SageFiniteRankFreeModule):
                return SageFiniteRankFreeModule.bases(self)
            assert isinstance(self, SageFreeModuleGeneric)
            return [self.basis()]

        @override
        def default_basis(self) -> object:
            if isinstance(self, SageFiniteRankFreeModule):
                return SageFiniteRankFreeModule.default_basis(self)
            assert isinstance(self, SageFreeModuleGeneric)
            return self.basis()

        @override
        def set_default_basis(self, basis: object) -> None:
            if isinstance(self, SageFiniteRankFreeModule):
                SageFiniteRankFreeModule.set_default_basis(self, basis)
                return
            assert isinstance(self, SageFreeModuleGeneric)
            if basis != self.basis():
                raise NotImplementedError

        @override
        def dimension(self) -> object:
            return self.rank()

        @override
        def exterior_power(self, degree: object) -> object:
            if isinstance(self, SageFiniteRankFreeModule):
                return SageFiniteRankFreeModule.exterior_power(self, degree)
            raise NotImplementedError

        @override
        def alternating_form(
            self,
            degree: object,
            name: str | None = None,
            latex_name: str | None = None,
        ) -> object:
            return SageFiniteRankFreeModule.alternating_form(
                self,
                degree,
                name=name,
                latex_name=latex_name,
            )
