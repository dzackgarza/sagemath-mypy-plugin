"""Local wrapper base classes — mirrors category_specs.cat.base_category_types.

This module defines a thin local wrapper around Sage's Category_singleton.
Fixtures that inherit from these classes (not from sage.categories directly)
expose whether the plugin correctly handles non-sage.categories namespaces.
"""
from sage.categories.category import Category as _SageBase


class LocalCategoryBase(_SageBase):
    """Minimal local wrapper.  Fixtures inherit from this, not from Sage directly."""
