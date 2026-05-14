"""Assigned cached_method in SubcategoryMethods should support override checking."""

from typing import override as _override

from sage.categories.category import Category
from sage.misc.cachefunc import cached_method


def _helper(self: object) -> int:
    return 1


class _AssignedCachedSubcategoryBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        endpoint = cached_method(_helper)


class _AssignedCachedSubcategorySub(Category):
    def super_categories(self):
        return [_AssignedCachedSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        @cached_method
        @_override
        def endpoint(self) -> int:
            return 2
