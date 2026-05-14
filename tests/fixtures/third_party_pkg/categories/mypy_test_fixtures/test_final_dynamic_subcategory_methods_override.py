"""Dynamic SubcategoryMethods override should honor @final like static inheritance."""

from typing import final, override as _override

from sage.categories.category import Category


class _FinalSubcategoryBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        @final
        def s(self) -> int:
            return 1


class _FinalSubcategorySub(Category):
    def super_categories(self):
        return [_FinalSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        @_override
        def s(self) -> int:
            return 2
