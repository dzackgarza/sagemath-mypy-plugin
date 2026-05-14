"""Transitive helper-alias ParentMethods override should honor @final."""

from typing import final, override as _override

from sage.categories.category import Category


class _TransitiveBaseParentMethods:
    @final
    def helper_parent_method(self) -> int:
        return 1


class _TransitiveMidParentMethods:
    pass


class _TransitiveSubParentMethods:
    @_override
    def helper_parent_method(self) -> int:
        return 3


class _TransitiveBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _TransitiveBaseParentMethods


class _TransitiveMid(Category):
    def super_categories(self):
        return [_TransitiveBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _TransitiveMidParentMethods


class _TransitiveSub(Category):
    def super_categories(self):
        return [_TransitiveMid.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _TransitiveSubParentMethods
