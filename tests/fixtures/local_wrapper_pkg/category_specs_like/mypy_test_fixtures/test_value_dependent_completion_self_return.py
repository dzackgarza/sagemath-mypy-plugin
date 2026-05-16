"""Value-dependent completion return where the zero-ideal branch returns self."""
from typing import TYPE_CHECKING

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase

if TYPE_CHECKING:
    from .value_dependent_completion_types import CompleteRing, Ideal


class _CompleteRings(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_CompleteRings":
        return cls()

    class ParentMethods:
        def is_complete_ring(self) -> bool:
            return True


class _Fields(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_Fields":
        return cls()

    class ParentMethods:
        def completion(self, ideal: "Ideal") -> "CompleteRing":
            if ideal.is_zero():
                return self  # [return-value] without plugin
            return _CompleteRings.ParentMethods()
