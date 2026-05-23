from __future__ import annotations

from sage.categories.category import Category


class InvalidPlainNested:
    class ParentMethods:
        def parent_self_surface(self) -> Category:
            return self.category()

    class SubcategoryMethods:
        def BoundSubcategory(self) -> Category:
            return self

        def category_self_attribute(self) -> Category:
            return self.base_category()


def uses_plain_nested_subcategory_method(instance: InvalidPlainNested) -> Category:
    return instance.BoundSubcategory()


class PlainAssignedRoot:
    ParentMethods: type[InvalidPlainNested.ParentMethods] = InvalidPlainNested.ParentMethods


class UnrelatedAssignedMethods:
    def unrelated(self) -> int:
        return 1


class PlainAssignedChild(PlainAssignedRoot):
    ParentMethods = UnrelatedAssignedMethods
