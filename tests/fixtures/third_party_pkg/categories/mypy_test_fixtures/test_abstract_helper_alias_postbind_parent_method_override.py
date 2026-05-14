"""Spurious abstractmethod error: helper-alias post-bound ParentMethods should be allowed."""

from abc import abstractmethod
from typing import override as _override

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractAliasPostbindBaseParentMethods:
    pass


_AbstractAliasPostbindBaseParentMethods.endpoint = endpoint


class _AbstractAliasPostbindSubParentMethods:
    @_override
    def endpoint(self) -> int:
        return 1


class _AbstractAliasPostbindParentBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _AbstractAliasPostbindBaseParentMethods


class _AbstractAliasPostbindParentSub(Category):
    def super_categories(self):
        return [_AbstractAliasPostbindParentBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _AbstractAliasPostbindSubParentMethods
