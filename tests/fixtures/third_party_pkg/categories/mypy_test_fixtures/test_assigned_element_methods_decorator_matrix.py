"""Assigned ElementMethods helpers should match static behavior across decorators."""

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


class _ElementPlainBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        method = _plain


class _ElementPlainSub(Category):
    def super_categories(self):
        return [_ElementPlainBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        @_override
        def method(self) -> int:
            return 2


class _ElementClassmethodBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        method = classmethod(_classmethod)


class _ElementClassmethodSub(Category):
    def super_categories(self):
        return [_ElementClassmethodBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        @classmethod
        @_override
        def method(cls) -> int:
            return 2


class _ElementStaticmethodBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        method = staticmethod(_staticmethod)


class _ElementStaticmethodSub(Category):
    def super_categories(self):
        return [_ElementStaticmethodBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        @staticmethod
        @_override
        def method() -> int:
            return 2


class _ElementPropertyBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        value = property(_property)


class _ElementPropertySub(Category):
    def super_categories(self):
        return [_ElementPropertyBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        @property
        @_override
        def value(self) -> int:
            return 2


class _ElementOverloadBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        method = _overload


class _ElementOverloadSub(Category):
    def super_categories(self):
        return [_ElementOverloadBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        @overload
        @_override
        def method(self, x: int) -> int: ...

        @overload
        @_override
        def method(self, x: str) -> str: ...

        @_override
        def method(self, x: int | str) -> int | str:
            return x
