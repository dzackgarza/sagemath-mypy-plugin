"""Spurious abstractmethod error: helper-alias MorphismMethods should be allowed."""

from abc import abstractmethod
from typing import override as _override

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractAliasBaseMorphismMethods:
    endpoint = endpoint


class _AbstractAliasSubMorphismMethods:
    @_override
    def endpoint(self) -> int:
        return 1


class _AbstractAliasMorphismBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    MorphismMethods = _AbstractAliasBaseMorphismMethods


class _AbstractAliasMorphismSub(Category):
    def super_categories(self):
        return [_AbstractAliasMorphismBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    MorphismMethods = _AbstractAliasSubMorphismMethods
