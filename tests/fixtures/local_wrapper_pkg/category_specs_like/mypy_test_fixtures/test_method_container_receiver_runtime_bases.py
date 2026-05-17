"""Method-container receiver aliases are valid Sage receiver base objects."""
from sage.categories.category import Category
from sage.structure.category_object import CategoryObject
from typing import override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _ReceiverParentMethods: ...


class _ReceiverCategory(LocalCategoryBase):
    ParentMethods = _ReceiverParentMethods

    class SubcategoryMethods: ...


type ReceiverObject = _ReceiverParentMethods


class _FirstReceiverBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_FirstReceiverBase":
        return cls()

    class ParentMethods:
        def left(self) -> int:
            return 1


class _SecondReceiverBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_SecondReceiverBase":
        return cls()

    class ParentMethods:
        def right(self) -> int:
            return 2


class _CombinedReceiverCategory(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_FirstReceiverBase.an_instance(), _SecondReceiverBase.an_instance()]

    @classmethod
    def an_instance(cls) -> "_CombinedReceiverCategory":
        return cls()

    class ParentMethods:
        @override
        def left(self) -> int:
            return 3

        @override
        def right(self) -> int:
            return 4


def _expects_category_object(obj: CategoryObject) -> CategoryObject:
    return obj


def _expects_category(category: Category) -> Category:
    return category


def parent_methods_receiver_is_category_object(
    parent: ReceiverObject,
) -> CategoryObject:
    return _expects_category_object(parent)


def subcategory_methods_receiver_is_category(
    subcategory: _ReceiverCategory.SubcategoryMethods,
) -> Category:
    return _expects_category(subcategory)


def projected_parent_methods_receiver_is_category_object(
    parent: _CombinedReceiverCategory.ParentMethods,
) -> CategoryObject:
    return _expects_category_object(parent)
