"""Aliased method-container providers see category receiver methods."""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _BaseRing:
    def one(self) -> int:
        return 1


class _ReceiverParentMethods:
    def one_from_base_ring(self) -> int:
        return self.base_ring().one()

    def ambient_category(self) -> "_AliasedReceiverCategory":
        return self.category()


class _AliasedReceiverCategory(LocalCategoryBase):
    def base_ring(self) -> _BaseRing:
        return _BaseRing()

    def category(self) -> "_AliasedReceiverCategory":
        return self

    ParentMethods = _ReceiverParentMethods
