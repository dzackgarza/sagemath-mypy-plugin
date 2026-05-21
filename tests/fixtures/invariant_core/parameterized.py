from __future__ import annotations

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.modules import Modules  # type: ignore[import-untyped]
from sage.categories.vector_spaces import VectorSpaces  # type: ignore[import-untyped]
from sage.rings.integer_ring import ZZ  # type: ignore[import-untyped]
from sage.rings.rational_field import QQ  # type: ignore[import-untyped]

ModulesOverIntegers = Modules(ZZ)
ModulesOverRationals = Modules(QQ)
VectorSpacesOverRationals = VectorSpaces(QQ)
