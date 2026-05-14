"""Helper-alias assigned SubcategoryMethods helpers should match static behavior."""

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


class _AliasPlainBaseSubcategoryMethods:
    method = _plain


class _AliasPlainSubSubcategoryMethods:
    @_override
    def method(self) -> int:
        return 2


class _AliasClassmethodBaseSubcategoryMethods:
    method = classmethod(_classmethod)


class _AliasClassmethodSubSubcategoryMethods:
    @classmethod
    @_override
    def method(cls) -> int:
        return 2


class _AliasStaticmethodBaseSubcategoryMethods:
    method = staticmethod(_staticmethod)


class _AliasStaticmethodSubSubcategoryMethods:
    @staticmethod
    @_override
    def method() -> int:
        return 2


class _AliasPropertyBaseSubcategoryMethods:
    value = property(_property)


class _AliasPropertySubSubcategoryMethods:
    @property
    @_override
    def value(self) -> int:
        return 2


class _AliasOverloadBaseSubcategoryMethods:
    method = _overload


class _AliasOverloadSubSubcategoryMethods:
    @overload
    @_override
    def method(self, x: int) -> int: ...

    @overload
    @_override
    def method(self, x: str) -> str: ...

    @_override
    def method(self, x: int | str) -> int | str:
        return x


class _AliasCachedBaseSubcategoryMethods:
    endpoint = cached_method(_plain)


class _AliasCachedSubSubcategoryMethods:
    @cached_method
    @_override
    def endpoint(self) -> int:
        return 2


class _AliasSubcategoryBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _AliasPlainBaseSubcategoryMethods


class _AliasSubcategorySubPlain(Category):
    def super_categories(self):
        return [_AliasSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _AliasPlainSubSubcategoryMethods


class _AliasSubcategorySubClassmethod(Category):
    def super_categories(self):
        return [_AliasSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _AliasClassmethodSubSubcategoryMethods


class _AliasSubcategorySubStaticmethod(Category):
    def super_categories(self):
        return [_AliasSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _AliasStaticmethodSubSubcategoryMethods


class _AliasSubcategorySubProperty(Category):
    def super_categories(self):
        return [_AliasSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _AliasPropertySubSubcategoryMethods


class _AliasSubcategorySubOverload(Category):
    def super_categories(self):
        return [_AliasSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _AliasOverloadSubSubcategoryMethods


class _AliasSubcategorySubCached(Category):
    def super_categories(self):
        return [_AliasSubcategoryBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    SubcategoryMethods = _AliasCachedSubSubcategoryMethods
