# NO from __future__ import annotations — annotations are evaluated eagerly.
# At runtime on Python ≥ 3.11, `-> Self` produces the actual typing.Self object
# (not the string "Self").  This exercises the _SELF_ANNOTATION_OBJECTS path in
# oracle._returns_typing_self, which is the only path NOT covered by
# provider_methods.py (which has from __future__ import annotations).
from typing import Self

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class SelfObjectCategory(LocalCategoryBase):
    def super_categories(self) -> list:
        return []

    class ParentMethods:
        def normalized(self) -> Self:
            return self
