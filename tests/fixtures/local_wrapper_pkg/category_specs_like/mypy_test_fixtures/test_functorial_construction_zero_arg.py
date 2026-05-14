"""FunctorialConstructionCategory subclasses called with zero args must not produce [call-arg].

In category_specs, constructions like Subobjects(), Quotients(), CartesianProducts(),
HomCategory() are called with zero args from SubcategoryMethods. Their __init__
declares base_category as a required positional argument, but at the call site the
category is supplied via __classcall_private__. The plugin must recognise these as
valid zero-arg calls.
"""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _SubobjectsCategory(LocalCategoryBase):
    """Minimal stand-in for a FunctorialConstructionCategory subclass."""

    def __init__(self, base_category: "_LocalBase") -> None:
        self._base = base_category

    @classmethod
    def an_instance(cls) -> "_SubobjectsCategory":
        return cls(_LocalBase.an_instance())

    class ParentMethods:
        pass


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class SubcategoryMethods:
        def subobjects(self) -> _SubobjectsCategory:
            return _SubobjectsCategory()  # zero-arg — must not be [call-arg]
