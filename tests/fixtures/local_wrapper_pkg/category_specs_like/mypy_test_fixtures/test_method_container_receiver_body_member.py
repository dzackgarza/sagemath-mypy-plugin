"""Method containers may call receiver methods through self."""
from __future__ import annotations

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _TensorCategory(LocalCategoryBase):
    def tensor_power(self, exponent: int) -> object:
        return exponent

    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_TensorCategory":
        return cls()

    class ParentMethods:
        def tensor_square(self) -> object:
            return self.tensor_power(2)
