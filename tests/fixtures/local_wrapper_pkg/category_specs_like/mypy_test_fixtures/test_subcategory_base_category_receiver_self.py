"""SubcategoryMethods self exposes Sage's base_category receiver method."""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _BaseRing:
    def one(self) -> int:
        return 1


class _BaseCategory(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_BaseCategory":
        return cls()

    def base_ring(self) -> _BaseRing:
        return _BaseRing()

    class SubcategoryMethods:
        def base_ring(self) -> _BaseRing:
            return self.base_category().base_ring()


class _RefinedCategory(LocalCategoryBase):
    _base_category_class_and_axiom = (_BaseCategory, "Refined")

    class SubcategoryMethods:
        def one_from_base_ring(self) -> int:
            return self.base_ring().one()
