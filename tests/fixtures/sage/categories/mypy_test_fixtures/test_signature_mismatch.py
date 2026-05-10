"""Test 9: Signature mismatch — B9.ParentMethods.@override f with incompatible signature.

A9.ParentMethods.f(x: int) → int.
B9.ParentMethods.@override f(x: str) → int → should FAIL (exit non-zero).
"""

from typing import override as _override

from sage.categories.category import Category


class _A9(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def f(self, x: int) -> int:
            """Ancestor method taking int parameter."""
            return x + 1


class _B9(Category):
    def super_categories(self):
        return [_A9.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def f(self, x: str) -> int:  # type: ignore[misc]  # EXPECTED FAIL: signature mismatch
            """Invalid @override — parameter type changed from int to str."""
            return len(x)
