"""Helper-alias assigned MorphismMethods helpers should match static behavior."""

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


class _AliasPlainBaseMorphismMethods:
    method = _plain


class _AliasPlainSubMorphismMethods:
    @_override
    def method(self) -> int:
        return 2


class _AliasClassmethodBaseMorphismMethods:
    method = classmethod(_classmethod)


class _AliasClassmethodSubMorphismMethods:
    @classmethod
    @_override
    def method(cls) -> int:
        return 2


class _AliasStaticmethodBaseMorphismMethods:
    method = staticmethod(_staticmethod)


class _AliasStaticmethodSubMorphismMethods:
    @staticmethod
    @_override
    def method() -> int:
        return 2


class _AliasPropertyBaseMorphismMethods:
    value = property(_property)


class _AliasPropertySubMorphismMethods:
    @property
    @_override
    def value(self) -> int:
        return 2


class _AliasOverloadBaseMorphismMethods:
    method = _overload


class _AliasOverloadSubMorphismMethods:
    @overload
    @_override
    def method(self, x: int) -> int: ...

    @overload
    @_override
    def method(self, x: str) -> str: ...

    @_override
    def method(self, x: int | str) -> int | str:
        return x


class _AliasMorphismBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    MorphismMethods = _AliasPlainBaseMorphismMethods


class _AliasMorphismSubPlain(Category):
    def super_categories(self):
        return [_AliasMorphismBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    MorphismMethods = _AliasPlainSubMorphismMethods


class _AliasMorphismSubClassmethod(Category):
    def super_categories(self):
        return [_AliasMorphismBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    MorphismMethods = _AliasClassmethodSubMorphismMethods


class _AliasMorphismSubStaticmethod(Category):
    def super_categories(self):
        return [_AliasMorphismBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    MorphismMethods = _AliasStaticmethodSubMorphismMethods


class _AliasMorphismSubProperty(Category):
    def super_categories(self):
        return [_AliasMorphismBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    MorphismMethods = _AliasPropertySubMorphismMethods


class _AliasMorphismSubOverload(Category):
    def super_categories(self):
        return [_AliasMorphismBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    MorphismMethods = _AliasOverloadSubMorphismMethods
