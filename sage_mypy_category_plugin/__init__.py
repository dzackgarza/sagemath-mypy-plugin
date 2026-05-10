"""
Sage Mypy Category Plugin: mypy plugin for Sage's dynamic category method system.

Makes @override (typing.override / typing_extensions.override) work for
Sage's ParentMethods, ElementMethods, MorphismMethods, and SubcategoryMethods
by injecting static base edges derived from Sage's runtime category resolution.
"""

__version__ = "0.1.0"
