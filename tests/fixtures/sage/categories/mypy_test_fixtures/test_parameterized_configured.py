"""Test 8: Parameterized category with basic instantiation verification.

Same parameterized category pattern as test_parameterized_no_config,
but additionally verifies that basic instantiation works in the Sage environment.

Expected: mypy passes (exit 0), instantiation does not crash.
"""

from typing import override as _override

from sage.categories.category import Category


class _ParamCat2(Category):
    """Parameterized category requiring a ring argument."""

    def __init__(self, base_ring):
        super().__init__()
        self._base_ring = base_ring

    def super_categories(self):
        return []

    class ParentMethods:
        def configured_op(self, x: int) -> int:
            """Method on a parameterized category — safe, no @override."""
            return x + 1


def _can_instantiate():
    """Quick sanity check — can we create an instance?"""
    cat = _ParamCat2("ZZ")
    assert hasattr(cat, "_base_ring")
    return True
