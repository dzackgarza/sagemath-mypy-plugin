"""Artificial Sage category fixtures for the mypy plugin test suite.

Each module in this package defines Category subclasses with method
containers (ParentMethods, ElementMethods, MorphismMethods) annotated
with @typing.override to verify the plugin correctly resolves Sage's
dynamic category resolution onto static base edges.
"""
