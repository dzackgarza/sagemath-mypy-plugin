"""Parameterized helper-alias ElementMethods override should honor @final."""

from typing import final, override as _override

from sage.categories.category import Category


class _ConfiguredAliasBaseElementMethods:
    @final
    def helper_parameterized_element_method(self) -> int:
        return 1


class _ConfiguredAliasSubElementMethods:
    @_override
    def helper_parameterized_element_method(self) -> int:
        return 2


class _ConfiguredAliasBase(Category):
    def __init__(self, base_ring):
        self._base_ring = base_ring
        super().__init__()

    def super_categories(self):
        return []

    ElementMethods = _ConfiguredAliasBaseElementMethods


class _ConfiguredAliasSub(Category):
    def __init__(self, base_ring):
        self._base_ring = base_ring
        super().__init__()

    def super_categories(self):
        return [_ConfiguredAliasBase(self._base_ring)]

    ElementMethods = _ConfiguredAliasSubElementMethods
