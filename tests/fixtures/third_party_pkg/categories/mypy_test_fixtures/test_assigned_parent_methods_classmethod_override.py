"""Assigned ParentMethods classmethod should support override checking."""

from typing import override as _override

from sage.categories.category import Category


def _helper(cls: type[object]) -> int:
    return 1


class _AssignedClassmethodBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        method = classmethod(_helper)


class _AssignedClassmethodSub(Category):
    def super_categories(self):
        return [_AssignedClassmethodBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @classmethod
        @_override
        def method(cls) -> int:
            return 2
