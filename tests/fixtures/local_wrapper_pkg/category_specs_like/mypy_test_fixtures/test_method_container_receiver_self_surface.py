"""Method-container self sees selected category receiver methods."""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _BaseRing:
    def one(self) -> int:
        return 1


class _ReceiverCategory(LocalCategoryBase):
    def base_ring(self) -> _BaseRing:
        return _BaseRing()

    def category(self) -> "_ReceiverCategory":
        return self

    class ParentMethods:
        def one_from_base_ring(self) -> int:
            return self.base_ring().one()

    class SubcategoryMethods:
        def ambient_category(self) -> "_ReceiverCategory":
            return self.category()
