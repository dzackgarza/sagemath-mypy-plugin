"""SubcategoryMethods __contains__ and ElementMethods operators must be usable.

In category_specs, two [operator] errors appear:
  1. `algebra in self` where self: SubcategoryMethods — requires __contains__
  2. `x != y` where x, y: ElementMethods — requires __ne__

The plugin must surface __contains__ on SubcategoryMethods and __ne__ on
ElementMethods so these operator expressions do not fire [operator] errors.
"""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class ElementMethods:
        def lt(self, other: "_LocalBase.ElementMethods") -> bool:
            return self.le(other) and self != other  # [operator] without plugin: != on ElementMethods

        def le(self, other: "_LocalBase.ElementMethods") -> bool:
            return True

    class SubcategoryMethods:
        def check_membership(self, obj: object) -> bool:
            return obj in self  # [operator] without plugin: `in SubcategoryMethods`
