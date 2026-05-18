"""Nested method containers inherit methods from a runtime Sage facade category."""
from typing import override as _override

from sage.categories.facade_sets import FacadeSets as SageFacadeSets
from sage.categories.sets_cat import Sets as SageSets

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _LocalFacadeSets(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [SageSets().Facade()]

    @classmethod
    def an_instance(cls) -> "_LocalFacadeSets":
        return cls()

    class ParentMethods:
        @_override
        def is_facade(self) -> bool:
            return True

        @_override
        def facade_for(self) -> tuple[object, ...] | bool:
            return SageFacadeSets.ParentMethods.facade_for(self)

        @_override
        def _an_element_(self) -> object:
            return SageFacadeSets.ParentMethods._an_element_(self)
