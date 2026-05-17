"""Source module for cross-module assigned method-container providers."""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class ImportedParentMethods:
    def imported_zero(self) -> int:
        return 0


class ImportedCategory(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "ImportedCategory":
        return cls()

    ParentMethods = ImportedParentMethods
