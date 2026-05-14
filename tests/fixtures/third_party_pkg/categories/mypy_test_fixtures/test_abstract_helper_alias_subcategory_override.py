"""Spurious abstractmethod error: helper-alias SubcategoryMethods should be allowed."""

from abc import abstractmethod
from typing import override as _override

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractAliasBaseSubcategoryMethods:
    endpoint = endpoint


class _AbstractAliasSubSubcategoryMethods:
    @_override
    def endpoint(self) -> int:
        return 1


class _AbstractAliasSubcategoryBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _AbstractAliasBaseSubcategoryMethods


class _AbstractAliasSubcategorySub(Category):
    def super_categories(self):
        return [_AbstractAliasSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _AbstractAliasSubSubcategoryMethods
