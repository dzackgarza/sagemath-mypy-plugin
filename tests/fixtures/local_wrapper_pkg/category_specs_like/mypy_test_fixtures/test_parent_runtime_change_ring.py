"""ParentMethods receiver self exposes Sage runtime parent methods."""
from __future__ import annotations

from typing import override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _FreeLikeModules(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:  # type: ignore[override]
        return []

    class ParentMethods:
        @override
        def _an_element_(self) -> object:
            return object()

        def base_ring(self) -> object:
            return object()

        def sample_element(self) -> object:
            return self._an_element_()

        def base_change(self) -> object:
            return self.change_ring(self.base_ring())
