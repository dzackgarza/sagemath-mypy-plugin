"""Helper-alias post-bound ElementMethods helpers should match static behavior."""

from typing import overload, override as _override

from sage.categories.category import Category


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


class _AliasPostbindBaseElementMethods:
    pass


_AliasPostbindBaseElementMethods.plain_method = _plain
_AliasPostbindBaseElementMethods.class_method = classmethod(_classmethod)
_AliasPostbindBaseElementMethods.static_method = staticmethod(_staticmethod)
_AliasPostbindBaseElementMethods.value = property(_property)
_AliasPostbindBaseElementMethods.overload_method = _overload


class _AliasPostbindSubElementMethods:
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


class _AliasPostbindElementBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _AliasPostbindBaseElementMethods


class _AliasPostbindElementSub(Category):
    def super_categories(self):
        return [_AliasPostbindElementBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _AliasPostbindSubElementMethods
