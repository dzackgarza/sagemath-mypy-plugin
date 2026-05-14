"""Assigned SubcategoryMethods helpers should match static behavior across decorators."""

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


class _SubcategoryPlainBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        method = _plain


class _SubcategoryPlainSub(Category):
    def super_categories(self):
        return [_SubcategoryPlainBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        @_override
        def method(self) -> int:
            return 2


class _SubcategoryClassmethodBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        method = classmethod(_classmethod)


class _SubcategoryClassmethodSub(Category):
    def super_categories(self):
        return [_SubcategoryClassmethodBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        @classmethod
        @_override
        def method(cls) -> int:
            return 2


class _SubcategoryStaticmethodBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        method = staticmethod(_staticmethod)


class _SubcategoryStaticmethodSub(Category):
    def super_categories(self):
        return [_SubcategoryStaticmethodBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        @staticmethod
        @_override
        def method() -> int:
            return 2


class _SubcategoryPropertyBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        value = property(_property)


class _SubcategoryPropertySub(Category):
    def super_categories(self):
        return [_SubcategoryPropertyBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        @property
        @_override
        def value(self) -> int:
            return 2


class _SubcategoryOverloadBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        method = _overload


class _SubcategoryOverloadSub(Category):
    def super_categories(self):
        return [_SubcategoryOverloadBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        @overload
        @_override
        def method(self, x: int) -> int: ...

        @overload
        @_override
        def method(self, x: str) -> str: ...

        @_override
        def method(self, x: int | str) -> int | str:
            return x


class _SubcategoryCachedBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        endpoint = cached_method(_plain)


class _SubcategoryCachedSub(Category):
    def super_categories(self):
        return [_SubcategoryCachedBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        @cached_method
        @_override
        def endpoint(self) -> int:
            return 2
