"""ParentMethods receiver self exposes Sage runtime parent methods."""
from __future__ import annotations

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _FreeLikeModules(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:  # type: ignore[override]
        return []

    class ParentMethods:
        def base_ring(self) -> object:
            return object()

        def base_change(self) -> object:
            return self.change_ring(self.base_ring())
