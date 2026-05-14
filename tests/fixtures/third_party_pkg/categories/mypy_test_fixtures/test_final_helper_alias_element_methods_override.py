"""Helper-alias ElementMethods override should honor @final."""

from typing import final, override as _override

from sage.categories.category import Category


class _FinalAliasBaseElementMethods:
    @final
    def helper_element_method(self) -> int:
        return 1


class _FinalAliasSubElementMethods:
    @_override
    def helper_element_method(self) -> int:
        return 2


class _FinalAliasBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _FinalAliasBaseElementMethods


class _FinalAliasSub(Category):
    def super_categories(self):
        return [_FinalAliasBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _FinalAliasSubElementMethods
