"""The written provider and the Sage category that compiles it."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sage.categories.category import Category
from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase

if TYPE_CHECKING:
    from . import Role


def evaluate_role(value: Role[int]) -> int:
    return value.echo(7)


class AliasCategory(LocalCategoryBase):
    def super_categories(self) -> list[Category]:
        return []

    class ParentMethods[T = int]:
        def echo(self, value: T) -> T:
            return value
