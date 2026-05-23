from __future__ import annotations

from typing import override

from sage.categories.category import Category
from sage.categories.covariant_functorial_construction import (
    FunctorialConstructionCategory,
)
from sage.structure.parent import Parent

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class Issue2Root(LocalCategoryBase):
    @override
    def super_categories(self) -> list[Category]:
        return []

    class ParentMethods:
        def source_backed_parent_method(self) -> int:
            return 1

    class SubcategoryMethods:
        def BoundSubcategory(self) -> Category:
            return self

        def category_self_argument(self) -> Category:
            return FunctorialConstructionCategory.category_of(self)

        def category_self_attribute(self) -> Category:
            return self.base_category()


class Issue2Child(LocalCategoryBase):
    @override
    def super_categories(self) -> list[Category]:
        return [Issue2Root()]

    class ParentMethods:
        @override
        def source_backed_parent_method(self) -> int:
            return 2

        def parent_self_surface(self) -> Category:
            return self.category()

        def parent_self_delegate(self) -> Parent:
            return self.an_element().parent()

    class SubcategoryMethods:
        def category_self_attribute_child(self) -> Category:
            return self.base_category()


def uses_projected_subcategory_method(category: Issue2Root) -> Category:
    return category.BoundSubcategory()


class RootAssignedParentMethods:
    def assigned_parent_method(self) -> int:
        return 1


class RefinedAssignedParentMethods:
    def refined_parent_method(self) -> int:
        return 2


class Issue2AssignedRoot(LocalCategoryBase):
    @override
    def super_categories(self) -> list[Category]:
        return []

    ParentMethods: type[RootAssignedParentMethods] = RootAssignedParentMethods


class Issue2AssignedChild(Issue2AssignedRoot):
    @override
    def super_categories(self) -> list[Category]:
        return [Issue2AssignedRoot()]

    ParentMethods = RefinedAssignedParentMethods
