"""Assigned ParentMethods property should support override checking."""

from typing import override as _override

from sage.categories.category import Category


def _helper(self: object) -> int:
    return 1


class _AssignedPropertyBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        value = property(_helper)


class _AssignedPropertySub(Category):
    def super_categories(self):
        return [_AssignedPropertyBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @property
        @_override
        def value(self) -> int:
            return 2
