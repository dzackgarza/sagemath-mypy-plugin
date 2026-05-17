"""Type aliases to aliased method-container providers expose provider methods."""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _ReceiverParentMethods:
    def zero(self) -> int:
        return 0


class _ReceiverCategory(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_ReceiverCategory":
        return cls()

    ParentMethods = _ReceiverParentMethods


type ReceiverObject = _ReceiverCategory.ParentMethods


def use_receiver_object(parent: ReceiverObject) -> int:
    return parent.zero()
