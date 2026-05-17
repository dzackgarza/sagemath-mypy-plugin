"""Arbitrary untyped method-container decorators must remain mypy errors."""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


def untyped_decorator(f):
    return f


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class SubcategoryMethods:
        @untyped_decorator
        def finite(self) -> "_LocalBase":
            return _LocalBase.an_instance()
