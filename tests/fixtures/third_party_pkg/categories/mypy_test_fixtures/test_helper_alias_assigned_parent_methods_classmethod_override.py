"""Helper alias with assigned classmethod should support override checking."""

from typing import override as _override

from sage.categories.category import Category


def _helper(cls: type[object]) -> int:
    return 1


class _HelperAliasClassmethodBaseParentMethods:
    method = classmethod(_helper)


class _HelperAliasClassmethodSubParentMethods:
    @classmethod
    @_override
    def method(cls) -> int:
        return 2


class _HelperAliasClassmethodBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _HelperAliasClassmethodBaseParentMethods


class _HelperAliasClassmethodSub(Category):
    def super_categories(self):
        return [_HelperAliasClassmethodBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _HelperAliasClassmethodSubParentMethods
