"""Helper alias with assigned staticmethod should support override checking."""

from typing import override as _override

from sage.categories.category import Category


def _helper() -> int:
    return 1


class _HelperAliasStaticmethodBaseParentMethods:
    method = staticmethod(_helper)


class _HelperAliasStaticmethodSubParentMethods:
    @staticmethod
    @_override
    def method() -> int:
        return 2


class _HelperAliasStaticmethodBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _HelperAliasStaticmethodBaseParentMethods


class _HelperAliasStaticmethodSub(Category):
    def super_categories(self):
        return [_HelperAliasStaticmethodBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _HelperAliasStaticmethodSubParentMethods
