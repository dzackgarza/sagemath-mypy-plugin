"""Test 1: Valid @override — B.ParentMethods.@override f, f exists in A.ParentMethods.

B.super_categories() → [A.an_instance()].
Expected: mypy passes (exit 0), no override errors.
"""

from typing import override as _override

from sage.categories.category import Category


class _A(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def f(self) -> int:
            """Ancestor method — provides the base for @override in _B."""
            return 1


class _B(Category):
    def super_categories(self):
        return [_A.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def f(self) -> int:
            """Valid @override — f is defined in _A.ParentMethods."""
            return 2
