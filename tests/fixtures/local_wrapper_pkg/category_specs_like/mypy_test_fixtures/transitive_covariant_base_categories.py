"""Shared semantic ancestors for the transitive covariant return fixture."""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _CompleteRings(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_CompleteRings":
        return cls()

    class ParentMethods:
        def completion(self) -> "_CompleteRings.ParentMethods":
            return self


class _CompleteDiscreteValuationRings(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_CompleteRings.an_instance()]

    @classmethod
    def an_instance(cls) -> "_CompleteDiscreteValuationRings":
        return cls()

    class ParentMethods:
        def uniformizer(self) -> int:
            return 2
