"""Test 5: MorphismMethods @override — B5.MorphismMethods.@override m, m exists in A5.MorphismMethods.

B5.super_categories() → [A5.an_instance()].
Expected: mypy passes (exit 0), no override errors.
"""

from typing import override as _override

from sage.categories.category import Category


class _A5(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        def m(self) -> int:
            """Ancestor morphism method."""
            return 1


class _B5(Category):
    def super_categories(self):
        return [_A5.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class MorphismMethods:
        @_override
        def m(self) -> int:
            """Valid @override — m is defined in _A5.MorphismMethods."""
            return 2
