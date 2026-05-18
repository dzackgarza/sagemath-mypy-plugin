from __future__ import annotations

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.modules import Modules  # type: ignore[import-untyped]
from sage.rings.rational_field import QQ  # type: ignore[import-untyped]

TensorProductsCategory = Modules(QQ).TensorProducts()
