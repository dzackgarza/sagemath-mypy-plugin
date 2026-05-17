"""Construction method containers inherit methods from their Python base."""
from typing import override

from sage.categories.category import Category
from sage.categories.cartesian_product import (
    CartesianProductFunctor,
    CartesianProductsCategory as _SageCartesianProductsCategory,
    cartesian_product,
)


class _LocalCartesianProductsBase(_SageCartesianProductsCategory):
    """Local wrapper around Sage's construction base, mirroring category_specs."""


class _CartesianProducts(_LocalCartesianProductsBase):
    @override
    def extra_super_categories(self) -> list[Category]:
        return [self.base_category()]

    class ParentMethods:
        @override
        def __init_extra__(self) -> None:
            pass


def accepts_cartesian_product_functor(
    functor: CartesianProductFunctor,
) -> CartesianProductFunctor:
    return functor


def category_from_parents(parents: object) -> object:
    return cartesian_product.category_from_parents(parents)
