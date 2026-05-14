"""Spurious final error: helper assigned into ElementMethods."""

from typing import final

from sage.categories.category import Category


@final
def endpoint(self: object) -> int:
    return 1


class _FinalAssignedElementBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        endpoint = endpoint
