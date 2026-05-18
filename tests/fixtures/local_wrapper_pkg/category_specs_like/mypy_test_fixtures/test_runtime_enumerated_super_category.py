"""Nested containers inherit methods from runtime Sage enumerated categories."""
from collections.abc import Iterator
from typing import override as _override

from sage.categories.enumerated_sets import EnumeratedSets as SageEnumeratedSets
from sage.categories.finite_enumerated_sets import (
    FiniteEnumeratedSets as SageFiniteEnumeratedSets,
)
from sage.categories.infinite_enumerated_sets import (
    InfiniteEnumeratedSets as SageInfiniteEnumeratedSets,
)

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _LocalEnumeratedSets(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [SageEnumeratedSets()]

    @classmethod
    def an_instance(cls) -> "_LocalEnumeratedSets":
        return cls()

    class ParentMethods:
        @_override
        def __iter__(self) -> Iterator[object]:
            return iter(())

        @_override
        def __getitem__(self, index: object) -> object:
            return index

        @_override
        def rank(self, element: object) -> object:
            return element

        @_override
        def is_empty(self) -> bool:
            return False

        @_override
        def is_countable(self) -> bool:
            return True

        @_override
        def __len__(self) -> int:
            return 0

        @_override
        def random_element(self) -> object:
            return object()


class _LocalFiniteEnumeratedSets(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [SageFiniteEnumeratedSets()]

    @classmethod
    def an_instance(cls) -> "_LocalFiniteEnumeratedSets":
        return cls()

    class ParentMethods:
        @_override
        def __len__(self) -> int:
            return 0

        @_override
        def cardinality(self) -> object:
            return 0

        @_override
        def random_element(self) -> object:
            return object()


class _LocalInfiniteEnumeratedSets(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [SageInfiniteEnumeratedSets()]

    @classmethod
    def an_instance(cls) -> "_LocalInfiniteEnumeratedSets":
        return cls()

    class ParentMethods:
        @_override
        def random_element(self) -> object:
            return object()
