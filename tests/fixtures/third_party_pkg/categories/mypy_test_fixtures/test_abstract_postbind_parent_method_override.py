"""Spurious abstractmethod error: post-definition rebound ParentMethods surface."""

from abc import abstractmethod
from typing import override as _override

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractPostbindBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        pass


_AbstractPostbindBase.ParentMethods.endpoint = endpoint


class _AbstractPostbindSub(Category):
    def super_categories(self):
        return [_AbstractPostbindBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def endpoint(self) -> int:
            return 1
