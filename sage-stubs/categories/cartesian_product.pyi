from typing import Any

from .category import Category


class CartesianProductFunctor: ...


class CartesianProductsCategory(Category):
    @classmethod
    def category_of(cls, category: Category, *args: Any, **kwargs: Any) -> Category: ...

    def base_category(self) -> Any: ...
    def extra_super_categories(self) -> Any: ...

    class ParentMethods:
        def __init_extra__(self) -> None: ...


class _CartesianProductCallable:
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...
    def category_from_parents(self, parents: Any) -> Any: ...


cartesian_product: _CartesianProductCallable
