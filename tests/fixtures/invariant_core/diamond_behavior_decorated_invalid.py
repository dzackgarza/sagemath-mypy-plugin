from __future__ import annotations

from typing import override

from tests.fixtures.invariant_core.diamond_behavior_decorated_base import (
    DecoratedBaseCategory,
)
from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class InvalidDecoratedOverrideCategory(LocalCategoryBase):
    @override
    def super_categories(self) -> list[LocalCategoryBase]:
        return [DecoratedBaseCategory.an_instance()]

    class ParentMethods:
        @property
        @override
        def decorated_property(self) -> str:
            return "property"

        @override
        @classmethod
        def decorated_classmethod(cls) -> str:
            return "classmethod"

        @override
        @staticmethod
        def decorated_staticmethod() -> str:
            return "staticmethod"

        @override
        def decorated_abstract(self) -> str:
            return "abstract"

        @override
        def decorated_overload(self, value: float) -> float:
            return value
