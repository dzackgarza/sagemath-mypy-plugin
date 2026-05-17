"""Axiom-base receiver methods are visible on SubcategoryMethods self."""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _BaseRing:
    def one(self) -> int:
        return 1


class _AxiomRoot(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_AxiomRoot":
        return cls()

    class SubcategoryMethods:
        def base_ring(self) -> _BaseRing:
            return _BaseRing()


class _AxiomBase(LocalCategoryBase):
    _base_category_class_and_axiom = (_AxiomRoot, "Base")


class _AxiomChild(LocalCategoryBase):
    _base_category_class_and_axiom = (_AxiomBase, "Refined")

    class SubcategoryMethods:
        def one_from_base_ring(self) -> int:
            return self.base_ring().one()
