"""The written provider and the Sage category that compiles it."""

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class AliasCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return []

    class ParentMethods[T]:
        def echo(self, value: T) -> T:
            return value
