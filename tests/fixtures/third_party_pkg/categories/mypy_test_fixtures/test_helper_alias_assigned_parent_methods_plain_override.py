"""Helper alias with assigned member should behave like a normal base method."""

from typing import override as _override

from sage.categories.category import Category


def _helper(self: object) -> int:
    return 1


class _HelperAliasBaseParentMethods:
    method = _helper


class _HelperAliasSubParentMethods:
    @_override
    def method(self) -> int:
        return 2


class _HelperAliasBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _HelperAliasBaseParentMethods


class _HelperAliasSub(Category):
    def super_categories(self):
        return [_HelperAliasBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _HelperAliasSubParentMethods
