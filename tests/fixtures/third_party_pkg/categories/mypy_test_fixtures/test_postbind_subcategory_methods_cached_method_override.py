"""Post-bound cached_method in SubcategoryMethods should support override checking."""

from typing import override as _override

from sage.categories.category import Category
from sage.misc.cachefunc import cached_method


def _helper(self: object) -> int:
    return 1


class _PostbindCachedSubcategoryBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        pass


_PostbindCachedSubcategoryBase.SubcategoryMethods.endpoint = cached_method(_helper)


class _PostbindCachedSubcategorySub(Category):
    def super_categories(self):
        return [_PostbindCachedSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        @cached_method
        @_override
        def endpoint(self) -> int:
            return 2
