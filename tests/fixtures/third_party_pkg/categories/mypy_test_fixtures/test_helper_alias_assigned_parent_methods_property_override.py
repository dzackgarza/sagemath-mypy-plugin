"""Helper alias with assigned property should support override checking."""

from typing import override as _override

from sage.categories.category import Category


def _helper(self: object) -> int:
    return 1


class _HelperAliasPropertyBaseParentMethods:
    value = property(_helper)


class _HelperAliasPropertySubParentMethods:
    @property
    @_override
    def value(self) -> int:
        return 2


class _HelperAliasPropertyBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _HelperAliasPropertyBaseParentMethods


class _HelperAliasPropertySub(Category):
    def super_categories(self):
        return [_HelperAliasPropertyBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _HelperAliasPropertySubParentMethods
