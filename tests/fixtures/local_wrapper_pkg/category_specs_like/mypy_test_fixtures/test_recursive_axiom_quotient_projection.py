"""Projected construction bases may need recursive static axiom bases."""
from collections.abc import Sequence
from typing import override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _ModuleParentMethods:
    def submodule(
        self,
        generators: Sequence[int] | Sequence[Sequence[int]],
        check: bool = True,
        already_echelonized: bool = False,
    ) -> object:
        return (tuple(generators), check, already_echelonized)

    def quotient_module(self, submodule: object, check: bool = True) -> object:
        return (submodule, check)


class _Quotients(LocalCategoryBase):
    def __init__(self, category: "_Modules") -> None:
        self._category = category

    def base_category(self) -> "_Modules":
        return self._category

    def super_categories(self):  # type: ignore[override]
        return [self.base_category().OverField(), _Subquotients.an_instance()]

    class ParentMethods:
        @override
        def quotient_module(self, submodule: object, check: bool = True) -> object:
            return (submodule, check)

        def quotient_by_generators(
            self,
            generators: Sequence[int],
            check: bool = True,
        ) -> object:
            return self.quotient_module(
                self.submodule(generators, check=check),
                check=check,
            )

        def quotient_by_relation_matrix(
            self,
            relation_matrix: Sequence[Sequence[int]],
            check: bool = True,
            already_echelonized: bool = False,
        ) -> object:
            return self.quotient_module(
                self.submodule(
                    relation_matrix,
                    check=check,
                    already_echelonized=already_echelonized,
                ),
                check=check,
            )


class _Modules(LocalCategoryBase):
    Quotients = _Quotients

    def OverField(self) -> "_OverField":
        return _OverField(self)

    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_Modules":
        return cls()

    ParentMethods = _ModuleParentMethods


class _OverField(LocalCategoryBase):
    _base_category_class_and_axiom = (_Modules, "OverField")

    def __init__(self, category: _Modules) -> None:
        self._category = category

    def base_category(self) -> _Modules:
        return self._category

    def super_categories(self):  # type: ignore[override]
        return []

    class ParentMethods:
        def linear_dependence(self) -> object:
            return object()


class _Subquotients(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_Subquotients":
        return cls()

    class ParentMethods: ...
