"""Assigned ParentMethods staticmethod should support override checking."""

from typing import override as _override

from sage.categories.category import Category


def _helper() -> int:
    return 1


class _AssignedStaticmethodBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        method = staticmethod(_helper)


class _AssignedStaticmethodSub(Category):
    def super_categories(self):
        return [_AssignedStaticmethodBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @staticmethod
        @_override
        def method() -> int:
            return 2
