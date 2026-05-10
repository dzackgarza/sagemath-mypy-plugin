"""Test 8: Parameterized category with an explicit configured representative."""

from typing import override as _override

from sage.categories.category import Category


class _ConfiguredParamBase(Category):
    """Parameterized category requiring a ring argument."""

    def __init__(self, base_ring):
        self._base_ring = base_ring
        super().__init__()

    def super_categories(self):
        return []

    class ParentMethods:
        def configured_op(self, x: int) -> int:
            return x + 1


class _ConfiguredParamSub(Category):
    """Subcategory whose semantic base is only visible with a representative."""

    def __init__(self, base_ring):
        self._base_ring = base_ring
        super().__init__()

    def super_categories(self):
        return [_ConfiguredParamBase(self._base_ring)]

    class ParentMethods:
        @_override
        def configured_op(self, x: int) -> int:
            return x + 2


def _can_instantiate():
    cat = _ConfiguredParamSub("ZZ")
    assert cat.super_categories()[0]._base_ring == "ZZ"
    return True
