"""Spurious final error: post-definition rebound MorphismMethods surface."""

from typing import final, override as _override

from sage.categories.category import Category


@final
def endpoint(self: object) -> int:
    return 1


class _FinalPostbindMorphismBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        pass


_FinalPostbindMorphismBase.MorphismMethods.endpoint = endpoint


class _FinalPostbindMorphismSub(Category):
    def super_categories(self):
        return [_FinalPostbindMorphismBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        @_override
        def endpoint(self) -> int:
            return 2
