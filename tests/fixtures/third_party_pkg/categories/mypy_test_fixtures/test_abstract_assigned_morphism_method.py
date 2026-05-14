"""Spurious abstractmethod error: helper assigned into MorphismMethods."""

from abc import abstractmethod

from sage.categories.category import Category


@abstractmethod
def endpoint(self: object) -> int: ...


class _AbstractAssignedMorphismBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        endpoint = endpoint
