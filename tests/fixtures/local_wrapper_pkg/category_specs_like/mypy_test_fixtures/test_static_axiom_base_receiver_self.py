"""Static axiom metadata gives method containers their semantic bases."""
from collections.abc import Sequence
from typing import override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _AxiomBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_AxiomBase":
        return cls()

    class ParentMethods:
        def inherited_value(self) -> int:
            return 1

        def submodule(self, generators: Sequence[int]) -> object:
            return tuple(generators)


class _AxiomChild(LocalCategoryBase):
    _base_category_class_and_axiom = (_AxiomBase, "Refined")

    class ParentMethods:
        @override
        def inherited_value(self) -> int:
            return 2

        def generated_submodule(self, generators: Sequence[int]) -> object:
            return self.submodule(generators)
