"""Real helper-class alias fixture for ParentMethods overrides.

This mirrors the category-spec pattern where the method container is a
top-level helper class assigned back onto the category class, rather than a
nested ``class ParentMethods`` declaration.
"""

from typing import override as _override

from sage.categories.category import Category


class _AliasBaseParentMethods:
    def helper_parent_method(self) -> int:
        return 1


class _AliasSubParentMethods:
    @_override
    def helper_parent_method(self) -> int:
        return 2


class _AliasBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _AliasBaseParentMethods


class _AliasSub(Category):
    def super_categories(self):
        return [_AliasBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ParentMethods = _AliasSubParentMethods
