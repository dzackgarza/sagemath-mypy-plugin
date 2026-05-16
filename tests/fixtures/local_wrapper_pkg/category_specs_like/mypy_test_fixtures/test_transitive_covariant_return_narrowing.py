"""Transitive covariant ParentMethods return narrowing through semantic bases."""
from typing import TYPE_CHECKING

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase

from .transitive_covariant_base_categories import (
    _CompleteDiscreteValuationRings,
)

if TYPE_CHECKING:
    from .transitive_covariant_types import CompleteRing


class _Zp(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_CompleteDiscreteValuationRings.an_instance()]

    @classmethod
    def an_instance(cls) -> "_Zp":
        return cls()

    class ParentMethods:
        def prime(self) -> int:
            return 2

        def completion(self) -> "CompleteRing":
            return self  # [return-value] without plugin
