"""Spurious final handling gap: helper-alias ElementMethods should see final base."""

from typing import final, override as _override

from sage.categories.category import Category


@final
def endpoint(self: object) -> int:
    return 1


class _FinalAliasBaseElementMethods:
    endpoint = endpoint


class _FinalAliasSubElementMethods:
    @_override
    def endpoint(self) -> int:
        return 2


class _FinalAliasElementBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _FinalAliasBaseElementMethods


class _FinalAliasElementSub(Category):
    def super_categories(self):
        return [_FinalAliasElementBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _FinalAliasSubElementMethods
