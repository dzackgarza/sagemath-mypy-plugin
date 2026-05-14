"""Spurious abstractmethod error: post-definition rebound SubcategoryMethods surface."""

from abc import abstractmethod
from typing import override as _override

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractPostbindSubcategoryBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        pass


_AbstractPostbindSubcategoryBase.SubcategoryMethods.endpoint = endpoint


class _AbstractPostbindSubcategorySub(Category):
    def super_categories(self):
        return [_AbstractPostbindSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        @_override
        def endpoint(self) -> int:
            return 1
