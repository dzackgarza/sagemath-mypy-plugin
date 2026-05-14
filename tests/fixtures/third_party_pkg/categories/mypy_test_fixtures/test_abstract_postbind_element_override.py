"""Spurious abstractmethod error: post-definition rebound ElementMethods surface."""

from abc import abstractmethod
from typing import override as _override

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractPostbindElementBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        pass


_AbstractPostbindElementBase.ElementMethods.endpoint = endpoint


class _AbstractPostbindElementSub(Category):
    def super_categories(self):
        return [_AbstractPostbindElementBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        @_override
        def endpoint(self) -> int:
            return 1
