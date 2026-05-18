"""ParentMethods may override methods from runtime objects passed to refine_category."""
from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


def refine_category(parent: object, categories: list[LocalCategoryBase]) -> object:
    return parent


class Constructors(LocalCategoryBase):
    def image(self, function: Callable[[object], object], domain: object) -> object:
        from local_wrapper_pkg.category_specs_like.mypy_test_fixtures.receiver_refine_runtime_source import (
            RuntimeImageSubobject as ProjectImageSubobject,
        )

        return refine_category(ProjectImageSubobject(function, domain), [_ImageSets()])


class _ImageSets(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_ImageSets":
        return cls()

    class ParentMethods:
        @override
        def __iter__(self) -> Iterator[object]:
            return iter(())

        @override
        def _an_element_(self) -> object:
            return object()
