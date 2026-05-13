"""Spurious final error: post-definition rebound ParentMethods surface."""

from typing import final, override as _override

from sage.categories.category import Category


@final
def endpoint(self: object) -> int:
    return 1


class _FinalPostbindBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        pass


_FinalPostbindBase.ParentMethods.endpoint = endpoint


class _FinalPostbindSub(Category):
    def super_categories(self):
        return [_FinalPostbindBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def endpoint(self) -> int:
            return 2
