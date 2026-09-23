"""Module-level relation functions sharing the compiler protocol's method names.

A category kernel can compute declared inheritance per category and role as
plain functions. The module then has attributes named like the compiler
protocol's methods, but it is not a compiler.
"""

from __future__ import annotations

from sage.categories.category import Category  # type: ignore[import-untyped]


def declared_inheritance(category: Category, role: str) -> tuple[type[object], ...]:
    return tuple(type(c) for c in category.super_categories())


def declared_subtyping(category: Category, role: str) -> tuple[Category, ...]:
    return tuple(category.super_categories())
