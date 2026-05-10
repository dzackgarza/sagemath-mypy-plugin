"""Fixture whose Sage category projection fails at runtime."""

from typing import override as _override

from sage.categories.category import Category


class _UnresolvedBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def inherited_op(self) -> int:
            return 1


class _UnresolvedSub(Category):
    def super_categories(self):
        raise RuntimeError("fixture projection failure")

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def inherited_op(self) -> int:
            return 2
