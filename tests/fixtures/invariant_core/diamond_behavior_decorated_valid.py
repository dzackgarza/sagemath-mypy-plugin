from __future__ import annotations

from typing import overload, override

from sage.categories.category import Category

from tests.fixtures.invariant_core.diamond_behavior_decorated_base import (
    DecoratedBaseCategory,
)
from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class ValidDecoratedOverrideCategory(LocalCategoryBase):
    @override
    def super_categories(self) -> list[Category]:
        return [DecoratedBaseCategory.an_instance()]

    class ParentMethods:
        @property
        @override
        def decorated_property(self) -> int:
            return 10

        @override
        @classmethod
        def decorated_classmethod(cls) -> int:
            return 20

        @override
        @staticmethod
        def decorated_staticmethod() -> int:
            return 30

        @override
        def decorated_abstract(self) -> int:
            return 40

        @overload
        def decorated_overload(self, value: int) -> int: ...

        @overload
        def decorated_overload(self, value: str) -> str: ...

        @override
        def decorated_overload(self, value: int | str) -> int | str:
            return value
