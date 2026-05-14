"""Helper alias with assigned cached_method should support override checking."""

from typing import override as _override

from sage.categories.category import Category
from sage.misc.cachefunc import cached_method


def _helper(self: object) -> int:
    return 1


class _HelperAliasCachedBaseSubcategoryMethods:
    endpoint = cached_method(_helper)


class _HelperAliasCachedSubSubcategoryMethods:
    @cached_method
    @_override
    def endpoint(self) -> int:
        return 2


class _HelperAliasCachedBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _HelperAliasCachedBaseSubcategoryMethods


class _HelperAliasCachedSub(Category):
    def super_categories(self):
        return [_HelperAliasCachedBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _HelperAliasCachedSubSubcategoryMethods
