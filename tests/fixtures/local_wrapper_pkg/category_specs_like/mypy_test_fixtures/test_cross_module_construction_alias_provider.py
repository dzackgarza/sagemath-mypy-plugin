"""Construction categories inherit methods from imported aliased providers."""
from collections.abc import Sequence
from typing import override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase
from local_wrapper_pkg.category_specs_like.mypy_test_fixtures.construction_alias_base import (
    _Modules,
)


class _Quotients(LocalCategoryBase):
    def __init__(self, category: _Modules) -> None:
        self._category = category

    def base_category(self) -> _Modules:
        return self._category

    def extra_super_categories(self) -> list[_Modules]:
        return [self.base_category()]

    def super_categories(self):  # type: ignore[override]
        return self.extra_super_categories()

    class ParentMethods:
        @override
        def quotient_module(self, submodule: object) -> object:
            return submodule

        def quotient_by_generators(self, generators: Sequence[int]) -> object:
            return self.quotient_module(self.submodule(generators))
