"""Fixture with a dynamic Sage base that has no source ParentMethods."""

from sage.categories.category import Category


class _NoSourceParentMethods(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()


class _NeedsSourceParentMethods(Category):
    def super_categories(self):
        return [_NoSourceParentMethods.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def local_op(self) -> int:
            return 1
