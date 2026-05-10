"""Test 4: ElementMethods @override — B4.ElementMethods.@override e, e exists in A4.ElementMethods.

B4.super_categories() → [A4.an_instance()].
Expected: mypy passes (exit 0), no override errors.
"""

from typing import override as _override

from sage.categories.category import Category


class _A4(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        def e(self) -> int:
            """Ancestor element method."""
            return 1


class _B4(Category):
    def super_categories(self):
        return [_A4.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ElementMethods:
        @_override
        def e(self) -> int:
            """Valid @override — e is defined in _A4.ElementMethods."""
            return 2
