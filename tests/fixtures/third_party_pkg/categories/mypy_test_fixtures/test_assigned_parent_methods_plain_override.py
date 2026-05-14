"""Assigned ParentMethods helper should behave like a normal base method."""

from typing import override as _override

from sage.categories.category import Category


def _helper(self: object) -> int:
    return 1


class _AssignedParentBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        method = _helper


class _AssignedParentSub(Category):
    def super_categories(self):
        return [_AssignedParentBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def method(self) -> int:
            return 2
