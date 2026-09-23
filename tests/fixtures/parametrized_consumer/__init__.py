"""Consumer whose categories take a base ring.

`PointedModules(R)` needs its base ring, so it has no nullary constructor.
Sage's `Category_over_base.an_instance()` supplies the sample object
(`PointedModules(QQ)`), which is how category discovery builds it.
"""

from __future__ import annotations

import sage.all  # type: ignore[import-untyped]  # noqa: F401
from sage.categories.category import Category  # type: ignore[import-untyped]
from sage.categories.category_types import Category_over_base_ring  # type: ignore[import-untyped]
from sage.categories.modules import Modules  # type: ignore[import-untyped]


class LocalCategoryOverBaseRing(Category_over_base_ring):
    """Local wrapper base for categories over a base ring."""


class PointedModules(LocalCategoryOverBaseRing):
    """Modules over the base ring with a chosen base point."""

    def super_categories(self) -> list[Category]:
        return [Modules(self.base_ring())]

    class ParentMethods:
        def base_point(self) -> object:
            return self.zero()  # type: ignore[attr-defined]
