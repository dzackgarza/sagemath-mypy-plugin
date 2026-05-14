"""Spurious final handling gap: helper-alias post-bound ElementMethods should see final base."""

from typing import final, override as _override

from sage.categories.category import Category


@final
def endpoint(self: object) -> int:
    return 1


class _FinalAliasPostbindBaseElementMethods:
    pass


_FinalAliasPostbindBaseElementMethods.endpoint = endpoint


class _FinalAliasPostbindSubElementMethods:
    @_override
    def endpoint(self) -> int:
        return 2


class _FinalAliasPostbindElementBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _FinalAliasPostbindBaseElementMethods


class _FinalAliasPostbindElementSub(Category):
    def super_categories(self):
        return [_FinalAliasPostbindElementBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    ElementMethods = _FinalAliasPostbindSubElementMethods
