"""Test 11: Cache invalidation — simple hierarchy for incremental rechecking.

Defines _A11 with ParentMethods.f and _B11 with ParentMethods.@override f.
The test will:
  1. Run mypy once (fresh) → should pass.
  2. Modify _A11 to remove or rename f.
  3. Run mypy again (incremental) → should fail.
"""

from typing import override as _override

from sage.categories.category import Category


class _A11(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def f(self) -> int:
            """Base method — will be removed during cache invalidation test."""
            return 1


class _B11(Category):
    def super_categories(self):
        return [_A11.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def f(self) -> int:
            """Valid @override — relies on _A11.ParentMethods.f."""
            return 2
