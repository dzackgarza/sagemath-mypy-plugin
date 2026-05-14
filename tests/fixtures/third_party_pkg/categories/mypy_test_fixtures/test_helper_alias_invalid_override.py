"""Helper-class alias misuse of @override with no ancestor definition."""

from typing import override as _override

from sage.categories.category import Category


class _AliasBaseElementMethods:
    def helper_base_method(self) -> int:
        return 1


class _AliasSubElementMethods:
    @_override
    def helper_missing_method(self) -> int:
        return 2


class _AliasBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _AliasBaseElementMethods


class _AliasSub(Category):
    def super_categories(self):
        return [_AliasBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _AliasSubElementMethods
