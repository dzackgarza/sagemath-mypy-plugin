"""Helper-alias assigned ElementMethods helpers should match static behavior."""

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


class _AliasPlainBaseElementMethods:
    method = _plain


class _AliasPlainSubElementMethods:
    @_override
    def method(self) -> int:
        return 2


class _AliasClassmethodBaseElementMethods:
    method = classmethod(_classmethod)


class _AliasClassmethodSubElementMethods:
    @classmethod
    @_override
    def method(cls) -> int:
        return 2


class _AliasStaticmethodBaseElementMethods:
    method = staticmethod(_staticmethod)


class _AliasStaticmethodSubElementMethods:
    @staticmethod
    @_override
    def method() -> int:
        return 2


class _AliasPropertyBaseElementMethods:
    value = property(_property)


class _AliasPropertySubElementMethods:
    @property
    @_override
    def value(self) -> int:
        return 2


class _AliasOverloadBaseElementMethods:
    method = _overload


class _AliasOverloadSubElementMethods:
    @overload
    @_override
    def method(self, x: int) -> int: ...

    @overload
    @_override
    def method(self, x: str) -> str: ...

    @_override
    def method(self, x: int | str) -> int | str:
        return x


class _AliasElementBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _AliasPlainBaseElementMethods
    PlainElementMethods = _AliasPlainBaseElementMethods
    ClassmethodElementMethods = _AliasClassmethodBaseElementMethods
    StaticmethodElementMethods = _AliasStaticmethodBaseElementMethods
    PropertyElementMethods = _AliasPropertyBaseElementMethods
    OverloadElementMethods = _AliasOverloadBaseElementMethods


class _AliasElementSubPlain(Category):
    def super_categories(self):
        return [_AliasElementBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _AliasPlainSubElementMethods


class _AliasElementSubClassmethod(Category):
    def super_categories(self):
        return [_AliasElementBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _AliasClassmethodSubElementMethods


class _AliasElementSubStaticmethod(Category):
    def super_categories(self):
        return [_AliasElementBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _AliasStaticmethodSubElementMethods


class _AliasElementSubProperty(Category):
    def super_categories(self):
        return [_AliasElementBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _AliasPropertySubElementMethods


class _AliasElementSubOverload(Category):
    def super_categories(self):
        return [_AliasElementBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _AliasOverloadSubElementMethods
