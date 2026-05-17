"""Cross-module aliases to assigned method-container providers are valid types."""
from local_wrapper_pkg.category_specs_like.mypy_test_fixtures.alias_provider_source import (
    ImportedCategory,
)


type ImportedObject = ImportedCategory.ParentMethods


def use_imported_object(parent: ImportedObject) -> int:
    return parent.imported_zero()
