"""Assigned SubcategoryMethods helper should behave like a normal base method."""

from typing import override as _override

from sage.categories.category import Category


def _helper(self: object) -> int:
    return 1


class _AssignedSubcategoryBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        endpoint = _helper


class _AssignedSubcategorySub(Category):
    def super_categories(self):
        return [_AssignedSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        @_override
        def endpoint(self) -> int:
            return 2
