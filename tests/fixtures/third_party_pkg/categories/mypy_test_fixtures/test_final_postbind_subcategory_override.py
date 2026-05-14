"""Spurious final error: post-definition rebound SubcategoryMethods surface."""

from typing import final, override as _override

from sage.categories.category import Category


@final
def endpoint(self: object) -> int:
    return 1


class _FinalPostbindSubcategoryBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        pass


_FinalPostbindSubcategoryBase.SubcategoryMethods.endpoint = endpoint


class _FinalPostbindSubcategorySub(Category):
    def super_categories(self):
        return [_FinalPostbindSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        @_override
        def endpoint(self) -> int:
            return 2
