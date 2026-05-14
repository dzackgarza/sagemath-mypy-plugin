"""Covariant return type narrowing of ParentMethods must not produce [return-value].

In category_specs, a subcategory method is declared (via @override) to return
BaseCategory.ParentMethods, but actually returns a more specific SubCategory.ParentMethods
instance. This is correct covariant narrowing in Sage's hierarchy — SubCategory.ParentMethods
IS semantically a BaseCategory.ParentMethods. mypy fires [return-value] because it has no
knowledge of the category hierarchy and treats the return types as unrelated classes.
The plugin must declare the subtype relationship.
"""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _BaseCategory(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_BaseCategory":
        return cls()

    class ParentMethods:
        def completion(self) -> "_BaseCategory.ParentMethods":
            return _BaseCategory.ParentMethods()


class _SubCategory(_BaseCategory):
    @classmethod
    def an_instance(cls) -> "_SubCategory":
        return cls()

    class ParentMethods:
        def completion(self) -> "_BaseCategory.ParentMethods":
            # Returns the sub's ParentMethods, which is a narrower type.
            # mypy fires [return-value] here because _SubCategory.ParentMethods
            # is not statically declared as a subtype of _BaseCategory.ParentMethods.
            return _SubCategory.ParentMethods()  # [return-value] without plugin
