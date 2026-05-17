"""A local-wrapper module whose leaf name collides with a top-level module."""
from typing import override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _CollisionBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    class ParentMethods:
        def collision_value(self) -> int:
            return 1


class _CollisionChild(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_CollisionBase.an_instance()]

    class ParentMethods:
        @override
        def collision_value(self) -> int:
            return 2
