"""Spurious final handling gap: helper-alias post-bound ParentMethods should see final base."""

from typing import final, override as _override

from sage.categories.category import Category


@final
def endpoint(self: object) -> int:
    return 1


class _FinalAliasPostbindBaseParentMethods:
    pass


_FinalAliasPostbindBaseParentMethods.endpoint = endpoint


class _FinalAliasPostbindSubParentMethods:
    @_override
    def endpoint(self) -> int:
        return 2


class _FinalAliasPostbindParentBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _FinalAliasPostbindBaseParentMethods


class _FinalAliasPostbindParentSub(Category):
    def super_categories(self):
        return [_FinalAliasPostbindParentBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _FinalAliasPostbindSubParentMethods
