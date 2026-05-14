"""Spurious abstractmethod error: helper-alias post-bound MorphismMethods should be allowed."""

from abc import abstractmethod
from typing import override as _override

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractAliasPostbindBaseMorphismMethods:
    pass


_AbstractAliasPostbindBaseMorphismMethods.endpoint = endpoint


class _AbstractAliasPostbindSubMorphismMethods:
    @_override
    def endpoint(self) -> int:
        return 1


class _AbstractAliasPostbindMorphismBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    MorphismMethods = _AbstractAliasPostbindBaseMorphismMethods


class _AbstractAliasPostbindMorphismSub(Category):
    def super_categories(self):
        return [_AbstractAliasPostbindMorphismBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    MorphismMethods = _AbstractAliasPostbindSubMorphismMethods
