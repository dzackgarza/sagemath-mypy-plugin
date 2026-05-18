"""Runtime receiver self includes inherited category parent methods."""
from collections.abc import Sequence

from sage.categories.category import Category

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _RootCategory(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_RootCategory":
        return cls()

    class ParentMethods:
        def submodule(self, generators: Sequence[int]) -> object:
            return tuple(generators)

        def tensor_power(self, exponent: int) -> object:
            return exponent

        def Hom(self, codomain: Category) -> object:
            return codomain


class _MiddleCategory(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_RootCategory.an_instance()]

    @classmethod
    def an_instance(cls) -> "_MiddleCategory":
        return cls()


class _LeafCategory(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_MiddleCategory.an_instance()]

    @classmethod
    def an_instance(cls) -> "_LeafCategory":
        return cls()

    class ParentMethods:
        def quotient_by_generators(self, generators: Sequence[int]) -> object:
            return self.submodule(generators)

        def square(self) -> object:
            return self.tensor_power(2)

        def endomorphism_set(self) -> object:
            return self.Hom(self.category())
