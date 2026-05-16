"""Construction categories inherit methods from their base category.

In category_specs, ``Modules(R).CartesianProducts()`` declares
``extra_super_categories() == [base_category()]``.  Its method containers may
therefore override module parent/element methods even when the Python source
does not explicitly subclass those method-container classes.
"""
from typing import override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _CartesianProducts(LocalCategoryBase):
    def __init__(self, category: "_Modules") -> None:
        self._category = category

    def base_category(self) -> "_Modules":
        return self._category

    def extra_super_categories(self) -> list["_Modules"]:
        return [self.base_category()]

    class ParentMethods:
        @override
        def __init_extra__(self) -> None:
            pass

    class ElementMethods:
        @override
        def _lmul_(self, scalar: object) -> object:
            return scalar


class _Modules(LocalCategoryBase):
    CartesianProducts = _CartesianProducts

    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_Modules":
        return cls()

    class ParentMethods:
        def __init_extra__(self) -> None:
            pass

    class ElementMethods:
        def _lmul_(self, scalar: object) -> object:
            return scalar
