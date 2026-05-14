"""Spurious abstractmethod error: helper assigned into ElementMethods."""

from abc import abstractmethod

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractAssignedElementBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        endpoint = endpoint
