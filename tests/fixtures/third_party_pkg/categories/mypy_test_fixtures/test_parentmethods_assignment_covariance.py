"""ParentMethods covariant assignment in subcategory homset.

A subcategory homset assigns a more specific standalone class to ParentMethods.
This is mathematically correct: methods on a subcategory are covariant functors
F': A' -> B' with A' <= A, B' <= B. The plugin must not fire [assignment] here.

Mirrors the real failure pattern in:
  category_specs/cat/homsets.py:126
  category_specs/sets/homsets.py:91
  category_specs/modules/homsets.py:193
  (and ~25 more homset files)
"""

from __future__ import annotations

from sage.categories.category import Category
from sage.categories.homset import HomCategory


class _BaseHomCategoryObjectMethods:
    def hom_count(self) -> int:
        return 0


class _SpecialHomCategoryObjectMethods(_BaseHomCategoryObjectMethods):
    def special_hom_property(self) -> str:
        return "special"


class BaseHomCat(HomCategory):
    ParentMethods = _BaseHomCategoryObjectMethods

    class ElementMethods: ...
    class MorphismMethods: ...


class SpecialHomCat(BaseHomCat):
    # Assigns a more specific ParentMethods — covariant, not a Liskov violation.
    ParentMethods = _SpecialHomCategoryObjectMethods

    class ElementMethods: ...
    class MorphismMethods: ...
