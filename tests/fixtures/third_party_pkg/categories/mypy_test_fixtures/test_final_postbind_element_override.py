"""Spurious final error: post-definition rebound ElementMethods surface."""

from typing import final, override as _override

from sage.categories.category import Category


@final
def endpoint(self: object) -> int:
    return 1


class _FinalPostbindElementBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        pass


_FinalPostbindElementBase.ElementMethods.endpoint = endpoint


class _FinalPostbindElementSub(Category):
    def super_categories(self):
        return [_FinalPostbindElementBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        @_override
        def endpoint(self) -> int:
            return 2
