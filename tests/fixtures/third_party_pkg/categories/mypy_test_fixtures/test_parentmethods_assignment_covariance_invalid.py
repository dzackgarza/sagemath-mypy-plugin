"""ParentMethods assignment with an unrelated class — must still be rejected.

Assigning a class that is NOT a subtype of the base ParentMethods should
remain a type error. The plugin's covariance allowance applies only to
genuine subcategory refinements, not arbitrary class assignments.
"""

from __future__ import annotations

from sage.categories.category import Category
from sage.categories.homset import HomCategory


class _BaseHomCategoryObjectMethods:
    def hom_count(self) -> int:
        return 0


class _UnrelatedClass:
    def something_else(self) -> str:
        return "unrelated"


class BaseHomCat(HomCategory):
    ParentMethods = _BaseHomCategoryObjectMethods

    class ElementMethods: ...
    class MorphismMethods: ...


class BrokenHomCat(BaseHomCat):
    # Assigns a completely unrelated class — this IS a genuine type error.
    ParentMethods = _UnrelatedClass  # type: ignore[assignment]

    class ElementMethods: ...
    class MorphismMethods: ...
