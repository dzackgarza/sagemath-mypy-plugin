"""Spurious final handling gap: helper-alias SubcategoryMethods should see final base."""

from typing import final, override as _override

from sage.categories.category import Category


@final
def endpoint(self: object) -> int:
    return 1


class _FinalAliasBaseSubcategoryMethods:
    endpoint = endpoint


class _FinalAliasSubSubcategoryMethods:
    @_override
    def endpoint(self) -> int:
        return 2


class _FinalAliasSubcategoryBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _FinalAliasBaseSubcategoryMethods


class _FinalAliasSubcategorySub(Category):
    def super_categories(self):
        return [_FinalAliasSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _FinalAliasSubSubcategoryMethods
