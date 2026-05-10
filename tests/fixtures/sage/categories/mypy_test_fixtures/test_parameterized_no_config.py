"""Test 7: Parameterized category without explicit config.

A parameterized category that requires constructor arguments (ring parameter).
Tests that the plugin does not crash when encountering such categories.
No @override decorators used — just checks that mypy can process the file.

Expected: mypy passes (exit 0), plugin handles parameterized categories gracefully.
"""

from typing import override as _override

from sage.categories.category import Category


class _ParamCat(Category):
    """A category that requires a ring parameter — cannot be instantiated via an_instance()."""

    def __init__(self, base_ring):
        super().__init__()
        self._base_ring = base_ring

    def super_categories(self):
        return []

    class ParentMethods:
        def custom_op(self, x: int) -> int:
            """Regular method — no @override, safe for parameterized categories."""
            return x * 2

    class ElementMethods:
        def element_op(self, other) -> int:
            """Element method — no @override."""
            return 0
