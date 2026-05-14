"""Real helper-class alias fixture for ElementMethods overrides.

This mirrors the category-spec pattern where the method container is a
top-level helper class assigned back onto the category class, rather than a
nested ``class ElementMethods`` declaration.
"""

from typing import override as _override

from sage.categories.category import Category


class _AliasBaseElementMethods:
    def helper_element_method(self) -> int:
        return 1


class _AliasSubElementMethods:
    @_override
    def helper_element_method(self) -> int:
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
