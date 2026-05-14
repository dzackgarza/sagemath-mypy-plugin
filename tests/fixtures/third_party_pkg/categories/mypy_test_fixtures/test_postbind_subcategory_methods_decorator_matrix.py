"""Post-bound SubcategoryMethods helpers should match static behavior."""

from typing import overload, override as _override

from sage.categories.category import Category
from sage.misc.cachefunc import cached_method


def _plain(self: object) -> int:
    return 1


def _classmethod(cls: type[object]) -> int:
    return 1


def _staticmethod() -> int:
    return 1


def _property(self: object) -> int:
    return 1


@overload
def _overload(self: object, x: int) -> int: ...


@overload
def _overload(self: object, x: str) -> str: ...


def _overload(self: object, x: int | str) -> int | str:
    return x


class _PostbindSubcategoryBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        pass


_PostbindSubcategoryBase.SubcategoryMethods.plain_method = _plain
_PostbindSubcategoryBase.SubcategoryMethods.class_method = classmethod(_classmethod)
_PostbindSubcategoryBase.SubcategoryMethods.static_method = staticmethod(_staticmethod)
_PostbindSubcategoryBase.SubcategoryMethods.value = property(_property)
_PostbindSubcategoryBase.SubcategoryMethods.overload_method = _overload
_PostbindSubcategoryBase.SubcategoryMethods.endpoint = cached_method(_plain)


class _PostbindSubcategorySub(Category):
    def super_categories(self):
        return [_PostbindSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        @_override
        def plain_method(self) -> int:
            return 2

        @classmethod
        @_override
        def class_method(cls) -> int:
            return 2

        @staticmethod
        @_override
        def static_method() -> int:
            return 2

        @property
        @_override
        def value(self) -> int:
            return 2

        @overload
        @_override
        def overload_method(self, x: int) -> int: ...

        @overload
        @_override
        def overload_method(self, x: str) -> str: ...

        @_override
        def overload_method(self, x: int | str) -> int | str:
            return x

        @cached_method
        @_override
        def endpoint(self) -> int:
            return 2
