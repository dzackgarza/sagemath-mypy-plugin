"""Spurious final handling gap: helper-alias post-bound SubcategoryMethods should see final base."""

from typing import final, override as _override

from sage.categories.category import Category


@final
def endpoint(self: object) -> int:
    return 1


class _FinalAliasPostbindBaseSubcategoryMethods:
    pass


_FinalAliasPostbindBaseSubcategoryMethods.endpoint = endpoint


class _FinalAliasPostbindSubSubcategoryMethods:
    @_override
    def endpoint(self) -> int:
        return 2


class _FinalAliasPostbindSubcategoryBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _FinalAliasPostbindBaseSubcategoryMethods


class _FinalAliasPostbindSubcategorySub(Category):
    def super_categories(self):
        return [_FinalAliasPostbindSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _FinalAliasPostbindSubSubcategoryMethods
