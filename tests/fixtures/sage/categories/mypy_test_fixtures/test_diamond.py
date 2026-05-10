"""Test 3: Diamond hierarchy — D3 inherits from B3 and C3, both inheriting from A3.

  A3
 /  \\
B3  C3
 \\  /
  D3

B3.ParentMethods.f and C3.ParentMethods.f define f (no @override — their own).
D3.ParentMethods.@override f → PASS (resolved from Sage — f exists in both B3 and C3).
"""

from typing import override as _override

from sage.categories.category import Category


class _A3(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        pass  # A3 does not define f


class _B3(Category):
    def super_categories(self):
        return [_A3.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def f(self) -> int:
            """Defines f in B3 — no @override here."""
            return 1


class _C3(Category):
    def super_categories(self):
        return [_A3.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def f(self) -> int:
            """Defines f in C3 — no @override here."""
            return 2


class _D3(Category):
    def super_categories(self):
        return [_B3.an_instance(), _C3.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def f(self) -> int:
            """Valid @override — f exists in both B3 and C3 ParentMethods."""
            return 3
