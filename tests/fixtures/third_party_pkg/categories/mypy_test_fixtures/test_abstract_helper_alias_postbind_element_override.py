"""Spurious abstractmethod error: helper-alias post-bound ElementMethods should be allowed."""

from abc import abstractmethod
from typing import override as _override

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractAliasPostbindBaseElementMethods:
    pass


_AbstractAliasPostbindBaseElementMethods.endpoint = endpoint


class _AbstractAliasPostbindSubElementMethods:
    @_override
    def endpoint(self) -> int:
        return 1


class _AbstractAliasPostbindElementBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _AbstractAliasPostbindBaseElementMethods


class _AbstractAliasPostbindElementSub(Category):
    def super_categories(self):
        return [_AbstractAliasPostbindElementBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _AbstractAliasPostbindSubElementMethods
