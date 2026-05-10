"""Test 6: Homsets override — B6.Homsets.ParentMethods.@override f.

A6 has a Homsets nested category. B6.Homsets → A6.Homsets.
A6.Homsets().ParentMethods defines f().
B6.Homsets.ParentMethods.@override f → PASS.
"""

from typing import override as _override

from sage.categories.category import Category


class _A6_Homsets(Category):
    """Nested Homsets category for A6."""

    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def f(self) -> int:
            """Ancestor Homsets ParentMethods method."""
            return 1


class _A6(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    @classmethod
    def Homsets(cls):
        return _A6_Homsets


class _B6_Homsets(Category):
    """Homsets category for B6 — inherits from A6.Homsets."""

    def super_categories(self):
        return [_A6.Homsets().an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def f(self) -> int:
            """Valid @override — f is defined in _A6.Homsets().ParentMethods."""
            return 2


class _B6(Category):
    def super_categories(self):
        return [_A6.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    @classmethod
    def Homsets(cls):
        return _B6_Homsets
