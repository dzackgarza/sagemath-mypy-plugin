"""Dynamic MorphismMethods override should honor @final like static inheritance."""

from typing import final, override as _override

from sage.categories.category import Category


class _FinalMorphismBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        @final
        def m(self) -> int:
            return 1


class _FinalMorphismSub(Category):
    def super_categories(self):
        return [_FinalMorphismBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        @_override
        def m(self) -> int:
            return 2
