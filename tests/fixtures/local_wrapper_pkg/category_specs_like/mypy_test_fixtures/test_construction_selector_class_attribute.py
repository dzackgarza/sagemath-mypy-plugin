"""Construction class attributes should still allow zero-arg selector calls.

In category_specs, a category class advertises construction category ownership
with assignments like ``Subobjects = _Subobjects``.  At runtime, Sage's category
machinery still makes ``C.Subobjects()`` the selector for the construction over
``C``.  Mypy must not treat that call as a direct constructor call requiring the
``category`` argument.
"""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _Subobjects(LocalCategoryBase):
    def __init__(self, category: "_TopologicalSpaces") -> None:
        self._category = category

    @classmethod
    def an_instance(cls) -> "_Subobjects":
        return cls(_TopologicalSpaces.an_instance())


class _TopologicalSpaces(LocalCategoryBase):
    Subobjects = _Subobjects

    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_TopologicalSpaces":
        return cls()


def subobjects_selector() -> _Subobjects:
    return _TopologicalSpaces.an_instance().Subobjects()
