"""Spurious abstractmethod error: helper-alias post-bound SubcategoryMethods should be allowed."""

from abc import abstractmethod
from typing import override as _override

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractAliasPostbindBaseSubcategoryMethods:
    pass


_AbstractAliasPostbindBaseSubcategoryMethods.endpoint = endpoint


class _AbstractAliasPostbindSubSubcategoryMethods:
    @_override
    def endpoint(self) -> int:
        return 1


class _AbstractAliasPostbindSubcategoryBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _AbstractAliasPostbindBaseSubcategoryMethods


class _AbstractAliasPostbindSubcategorySub(Category):
    def super_categories(self):
        return [_AbstractAliasPostbindSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _AbstractAliasPostbindSubSubcategoryMethods
