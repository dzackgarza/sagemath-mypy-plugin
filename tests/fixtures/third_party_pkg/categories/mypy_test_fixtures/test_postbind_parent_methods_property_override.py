"""Post-bound ParentMethods property should support override checking."""

from typing import override as _override

from sage.categories.category import Category


def _helper(self: object) -> int:
    return 1


class _PostbindPropertyBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        pass


_PostbindPropertyBase.ParentMethods.value = property(_helper)


class _PostbindPropertySub(Category):
    def super_categories(self):
        return [_PostbindPropertyBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @property
        @_override
        def value(self) -> int:
            return 2
