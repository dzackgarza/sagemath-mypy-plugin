"""Spurious final error: helper assigned into ParentMethods."""

from typing import final

from sage.categories.category import Category


@final
def structure_domain(self: object) -> int:
    return 1


class _FinalAssignedParentBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        structure_domain = structure_domain
