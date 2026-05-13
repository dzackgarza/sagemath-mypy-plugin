"""Spurious final handling gap: helper-alias override should see final base."""

from typing import final, override as _override

from sage.categories.category import Category


@final
def helper_parent_method(self: object) -> int:
    return 1


class _FinalAliasBaseParentMethods:
    helper_parent_method = helper_parent_method


class _FinalAliasSubParentMethods:
    @_override
    def helper_parent_method(self) -> int:
        return 2


class _FinalAliasBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _FinalAliasBaseParentMethods


class _FinalAliasSub(Category):
    def super_categories(self):
        return [_FinalAliasBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _FinalAliasSubParentMethods
