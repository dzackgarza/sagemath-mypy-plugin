"""Spurious abstractmethod error: helper assigned into ParentMethods."""

from abc import abstractmethod

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractAssignedParentBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        endpoint = endpoint
