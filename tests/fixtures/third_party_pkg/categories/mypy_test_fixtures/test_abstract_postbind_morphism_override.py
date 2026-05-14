"""Spurious abstractmethod error: post-definition rebound MorphismMethods surface."""

from abc import abstractmethod
from typing import override as _override

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractPostbindMorphismBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        pass


_AbstractPostbindMorphismBase.MorphismMethods.endpoint = endpoint


class _AbstractPostbindMorphismSub(Category):
    def super_categories(self):
        return [_AbstractPostbindMorphismBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        @_override
        def endpoint(self) -> int:
            return 1
