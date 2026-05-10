"""Test 2: Invalid @override — B2.ParentMethods.@override g, g absent from all ancestors.

B2.super_categories() → [A2.an_instance()].
Expected: mypy fails (exit non-zero), "no base method was found" in stderr.
"""

from typing import override as _override

from sage.categories.category import Category


class _A2(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def f(self) -> int:
            return 1


class _B2(Category):
    def super_categories(self):
        return [_A2.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def g(self) -> int:  # type: ignore[misc]  # EXPECTED FAIL: g not in any ancestor
            """Invalid @override — g does not exist in _A2.ParentMethods."""
            return 2
