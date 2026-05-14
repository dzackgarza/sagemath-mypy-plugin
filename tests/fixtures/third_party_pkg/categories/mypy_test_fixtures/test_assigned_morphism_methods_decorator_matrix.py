"""Assigned MorphismMethods helpers should match static behavior across decorators."""

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


class _MorphismPlainBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        method = _plain


class _MorphismPlainSub(Category):
    def super_categories(self):
        return [_MorphismPlainBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        @_override
        def method(self) -> int:
            return 2


class _MorphismClassmethodBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        method = classmethod(_classmethod)


class _MorphismClassmethodSub(Category):
    def super_categories(self):
        return [_MorphismClassmethodBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        @classmethod
        @_override
        def method(cls) -> int:
            return 2


class _MorphismStaticmethodBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        method = staticmethod(_staticmethod)


class _MorphismStaticmethodSub(Category):
    def super_categories(self):
        return [_MorphismStaticmethodBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        @staticmethod
        @_override
        def method() -> int:
            return 2


class _MorphismPropertyBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        value = property(_property)


class _MorphismPropertySub(Category):
    def super_categories(self):
        return [_MorphismPropertyBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        @property
        @_override
        def value(self) -> int:
            return 2


class _MorphismOverloadBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        method = _overload


class _MorphismOverloadSub(Category):
    def super_categories(self):
        return [_MorphismOverloadBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        @overload
        @_override
        def method(self, x: int) -> int: ...

        @overload
        @_override
        def method(self, x: str) -> str: ...

        @_override
        def method(self, x: int | str) -> int | str:
            return x
