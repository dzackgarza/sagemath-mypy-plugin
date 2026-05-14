"""Helper alias with assigned overloads should support override checking."""

from typing import overload, override as _override

from sage.categories.category import Category


@overload
def _helper(self: object, x: int) -> int: ...


@overload
def _helper(self: object, x: str) -> str: ...


def _helper(self: object, x: int | str) -> int | str:
    return x


class _HelperAliasOverloadBaseParentMethods:
    method = _helper


class _HelperAliasOverloadSubParentMethods:
    @overload
    @_override
    def method(self, x: int) -> int: ...

    @overload
    @_override
    def method(self, x: str) -> str: ...

    @_override
    def method(self, x: int | str) -> int | str:
        return x


class _HelperAliasOverloadBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _HelperAliasOverloadBaseParentMethods


class _HelperAliasOverloadSub(Category):
    def super_categories(self):
        return [_HelperAliasOverloadBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _HelperAliasOverloadSubParentMethods
