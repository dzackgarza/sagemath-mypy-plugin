from __future__ import annotations

from typing import override

from tests.fixtures.invariant_core.diamond_runtime import BottomCategory
from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class SignatureBaseCategory(LocalCategoryBase):
    @override
    def super_categories(self) -> list[LocalCategoryBase]:
        return [BottomCategory.an_instance()]

    class ParentMethods:
        def signature_method(self, value: int) -> int:
            return value


class SignatureMismatchCategory(LocalCategoryBase):
    @override
    def super_categories(self) -> list[LocalCategoryBase]:
        return [SignatureBaseCategory.an_instance()]

    class ParentMethods:
        @override
        def signature_method(self, value: str) -> int:
            return len(value)
