"""Dynamic ElementMethods override should honor @final like static inheritance."""

from typing import final, override as _override

from sage.categories.category import Category


class _FinalElementBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        @final
        def e(self) -> int:
            return 1


class _FinalElementSub(Category):
    def super_categories(self):
        return [_FinalElementBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        @_override
        def e(self) -> int:
            return 2
