"""Test 10: Renamed ancestor — valid override to be modified at test time.

This fixture is designed to be copied and modified during test execution.
The test function will:
  1. Copy this file to a temp location.
  2. Run mypy on it (should pass — valid override).
  3. Remove the ancestor method (rename it or delete it).
  4. Run mypy again (should fail — now there's no base method).

Initial state: _B10.@override f, _A10.ParentMethods defines f → PASS.
"""

from typing import override as _override

from sage.categories.category import Category


class _A10(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        # TARGET_RENAME: f_to_be_deleted
        def f_to_be_deleted(self) -> int:
            """This method will be renamed/removed at test time."""
            return 1


class _B10(Category):
    def super_categories(self):
        return [_A10.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def f_to_be_deleted(self) -> int:
            """Overrides the ancestor method — valid until ancestor is modified."""
            return 2
