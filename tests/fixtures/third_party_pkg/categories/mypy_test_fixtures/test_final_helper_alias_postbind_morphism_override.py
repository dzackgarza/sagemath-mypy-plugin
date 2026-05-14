"""Spurious final handling gap: helper-alias post-bound MorphismMethods should see final base."""

from typing import final, override as _override

from sage.categories.category import Category


@final
def endpoint(self: object) -> int:
    return 1


class _FinalAliasPostbindBaseMorphismMethods:
    pass


_FinalAliasPostbindBaseMorphismMethods.endpoint = endpoint


class _FinalAliasPostbindSubMorphismMethods:
    @_override
    def endpoint(self) -> int:
        return 2


class _FinalAliasPostbindMorphismBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    MorphismMethods = _FinalAliasPostbindBaseMorphismMethods


class _FinalAliasPostbindMorphismSub(Category):
    def super_categories(self):
        return [_FinalAliasPostbindMorphismBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    MorphismMethods = _FinalAliasPostbindSubMorphismMethods
