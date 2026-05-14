"""Transitive helper-class alias fixture for ElementMethods overrides."""

from typing import override as _override

from sage.categories.category import Category


class _TransitiveBaseElementMethods:
    def helper_element_method(self) -> int:
        return 1


class _TransitiveMidElementMethods:
    pass


class _TransitiveSubElementMethods:
    @_override
    def helper_element_method(self) -> int:
        return 3


class _TransitiveBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _TransitiveBaseElementMethods


class _TransitiveMid(Category):
    def super_categories(self):
        return [_TransitiveBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _TransitiveMidElementMethods


class _TransitiveSub(Category):
    def super_categories(self):
        return [_TransitiveMid.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _TransitiveSubElementMethods
