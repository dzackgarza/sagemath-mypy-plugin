"""Parameterized helper-class alias fixture for ParentMethods overrides."""

from typing import override as _override

from sage.categories.category import Category


class _ConfiguredAliasBaseParentMethods:
    def helper_parameterized_parent_method(self) -> int:
        return 1


class _ConfiguredAliasSubParentMethods:
    @_override
    def helper_parameterized_parent_method(self) -> int:
        return 2


class _ConfiguredAliasBase(Category):
    def __init__(self, base_ring):
        self._base_ring = base_ring
        super().__init__()

    def super_categories(self):
        return []

    ParentMethods = _ConfiguredAliasBaseParentMethods


class _ConfiguredAliasSub(Category):
    def __init__(self, base_ring):
        self._base_ring = base_ring
        super().__init__()

    def super_categories(self):
        return [_ConfiguredAliasBase(self._base_ring)]

    ParentMethods = _ConfiguredAliasSubParentMethods
