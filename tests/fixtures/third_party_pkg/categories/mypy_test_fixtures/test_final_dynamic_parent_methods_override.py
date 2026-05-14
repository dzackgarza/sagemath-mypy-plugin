"""Dynamic ParentMethods override should honor @final like static inheritance."""

from typing import final, override as _override

from sage.categories.category import Category


class _FinalParentBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @final
        def f(self) -> int:
            return 1


class _FinalParentSub(Category):
    def super_categories(self):
        return [_FinalParentBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def f(self) -> int:
            return 2
