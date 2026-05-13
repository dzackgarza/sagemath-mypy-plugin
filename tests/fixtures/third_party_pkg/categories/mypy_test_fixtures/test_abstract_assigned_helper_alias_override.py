"""Spurious abstractmethod error: helper-alias override should be allowed."""

from abc import abstractmethod
from typing import override as _override

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractAliasBaseParentMethods:
    endpoint = endpoint


class _AbstractAliasSubParentMethods:
    @_override
    def endpoint(self) -> int:
        return 1


class _AbstractAliasBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _AbstractAliasBaseParentMethods


class _AbstractAliasSub(Category):
    def super_categories(self):
        return [_AbstractAliasBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _AbstractAliasSubParentMethods
