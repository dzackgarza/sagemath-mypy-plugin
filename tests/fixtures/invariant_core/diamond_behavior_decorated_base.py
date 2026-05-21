from __future__ import annotations

from abc import abstractmethod
from typing import overload, override

from tests.fixtures.invariant_core.diamond_runtime import BottomCategory
from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class DecoratedBaseCategory(LocalCategoryBase):
    @override
    def super_categories(self) -> list[LocalCategoryBase]:
        return [BottomCategory.an_instance()]

    class ParentMethods:
        @property
        def decorated_property(self) -> int:
            return 1

        @classmethod
        def decorated_classmethod(cls) -> int:
            return 2

        @staticmethod
        def decorated_staticmethod() -> int:
            return 3

        @abstractmethod
        def decorated_abstract(self) -> int:
            raise NotImplementedError

        @overload
        def decorated_overload(self, value: int) -> int: ...

        @overload
        def decorated_overload(self, value: str) -> str: ...

        def decorated_overload(self, value: int | str) -> int | str:
            return value
