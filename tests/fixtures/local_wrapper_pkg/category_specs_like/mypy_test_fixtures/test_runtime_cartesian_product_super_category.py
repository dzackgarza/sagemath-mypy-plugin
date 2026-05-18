"""Nested containers inherit methods from Sage Sets().CartesianProducts()."""
from typing import override as _override

from sage.categories.cartesian_product import CartesianProductsCategory
from sage.categories.sets_cat import Sets as SageSets

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase

_CARTESIAN_PRODUCT_CATEGORY_TYPE: type[CartesianProductsCategory] = (
    CartesianProductsCategory
)


class _LocalCartesianProducts(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [SageSets().CartesianProducts()]

    @classmethod
    def an_instance(cls) -> "_LocalCartesianProducts":
        return cls()

    class ParentMethods:
        @_override
        def cardinality(self) -> object:
            return SageSets.CartesianProducts.ParentMethods.cardinality(self)

        @_override
        def is_finite(self) -> bool:
            return SageSets.CartesianProducts.ParentMethods.is_finite(self)

        @_override
        def _element_constructor_(self, element: object) -> object:
            return element

        @_override
        def __contains__(self, element: object) -> bool:
            return bool(element)

        @_override
        def construction(self) -> object:
            return object()

        @_override
        def _coerce_map_from_(self, source: object) -> object:
            return source

        @_override
        def _sympy_(self) -> object:
            return SageSets.CartesianProducts.ParentMethods._sympy_(self)
