"""Spurious final handling gap: helper-alias MorphismMethods should see final base."""

from typing import final, override as _override

from sage.categories.category import Category


@final
def endpoint(self: object) -> int:
    return 1


class _FinalAliasBaseMorphismMethods:
    endpoint = endpoint


class _FinalAliasSubMorphismMethods:
    @_override
    def endpoint(self) -> int:
        return 2


class _FinalAliasMorphismBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    MorphismMethods = _FinalAliasBaseMorphismMethods


class _FinalAliasMorphismSub(Category):
    def super_categories(self):
        return [_FinalAliasMorphismBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    MorphismMethods = _FinalAliasSubMorphismMethods
