"""Spurious abstractmethod error: helper-alias ElementMethods should be allowed."""

from abc import abstractmethod
from typing import override as _override

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractAliasBaseElementMethods:
    endpoint = endpoint


class _AbstractAliasSubElementMethods:
    @_override
    def endpoint(self) -> int:
        return 1


class _AbstractAliasElementBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _AbstractAliasBaseElementMethods


class _AbstractAliasElementSub(Category):
    def super_categories(self):
        return [_AbstractAliasElementBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _AbstractAliasSubElementMethods
