"""Parameterized helper-class alias fixture.

This mirrors category-spec construction categories whose method containers are
top-level helper classes while the owning category requires representative
arguments for instantiation.
"""

from typing import override as _override

from sage.categories.category import Category


class _ConfiguredAliasBaseElementMethods:
    def helper_parameterized_method(self) -> int:
        return 1


class _ConfiguredAliasSubElementMethods:
    @_override
    def helper_parameterized_method(self) -> int:
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
