"""Fixture whose projected source container is absent from mypy's module graph."""

from typing import override as _override

from sage.categories.category import Category


class _MissingTypeInfoBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        __module__ = "sage.categories.mypy_test_fixtures.not_loaded_by_mypy"

        def inherited_op(self) -> int:
            return 1


class _MissingTypeInfoSub(Category):
    def super_categories(self):
        return [_MissingTypeInfoBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def inherited_op(self) -> int:
            return 2
