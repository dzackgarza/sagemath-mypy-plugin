from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, cast, final

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.category import Category  # type: ignore[import-untyped]
from sage.categories.category_singleton import Category_singleton  # type: ignore[import-untyped]
from sage.categories.category_with_axiom import CategoryWithAxiom_singleton  # type: ignore[import-untyped]
from sage.categories.homsets import Homsets as SageHomsets  # type: ignore[import-untyped]
from sage.categories.homsets import HomsetsCategory  # type: ignore[import-untyped]
from sage.categories.objects import Objects  # type: ignore[import-untyped]
from sage.misc.constant_function import ConstantFunction  # type: ignore[import-untyped]
from sage.misc.lazy_import import LazyImport  # type: ignore[import-untyped]
from sage.structure.dynamic_class import DynamicMetaclass  # type: ignore[import-untyped]

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class _HomsetsWithEndset(Protocol):
    def Endset(self) -> object: ...


def _sage_homsets_endset() -> Category:
    return cast(Category, cast(_HomsetsWithEndset, SageHomsets()).Endset())


class TopCategory(LocalCategoryBase):
    def super_categories(self) -> list[object]:
        return [Objects()]

    class Homsets(HomsetsCategory):
        def extra_super_categories(self) -> Sequence[Category]:
            return []

        class ParentMethods:
            def top_homset_parent(self) -> int:
                return 1

        class ElementMethods:
            def top_homset_element(self) -> int:
                return 10


class BottomCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [TopCategory.an_instance()]

    def is_full_subcategory(self, category: object) -> bool:
        return category is TopCategory.an_instance()

    class Homsets(HomsetsCategory):
        def extra_super_categories(self) -> Sequence[Category]:
            return []

        class ParentMethods:
            def bottom_homset_parent(self) -> int:
                return 2

        class ElementMethods:
            def bottom_homset_element(self) -> int:
                return 20


class _SingletonClasscallMixin:
    @staticmethod
    @final
    def __classcall__(cls: type[Category_singleton]) -> object:
        if isinstance(cls, DynamicMetaclass):
            cls = cls.__base__
        obj = cast(Any, super(Category_singleton, cls)).__classcall__(cls)
        cast(Any, cls)._set_classcall(ConstantFunction(obj))
        cast(Any, obj.__class__)._set_classcall(ConstantFunction(obj))
        return obj


class LocalHomsetsBase(_SingletonClasscallMixin, SageHomsets):
    pass


class SharedHomsetParentMethods:
    def shared_homset_parent(self) -> int:
        return 1


class SharedStandaloneHomCategory(LocalHomsetsBase):
    def super_categories(self) -> list[object]:
        return [Objects()]

    ParentMethods = cast(type[SageHomsets.ParentMethods], SharedHomsetParentMethods)


class SharedHomsetProviderCategory(LocalCategoryBase):
    def super_categories(self) -> list[object]:
        return [Objects()]

    class Homsets(HomsetsCategory):
        def super_categories(self) -> list[object]:
            return [SharedStandaloneHomCategory()]

        ParentMethods = cast(type[SageHomsets.ParentMethods], SharedHomsetParentMethods)


class RefinedSharedHomsetProviderCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return [SharedHomsetProviderCategory.an_instance()]

    def is_full_subcategory(self, category: object) -> bool:
        return category is SharedHomsetProviderCategory.an_instance()

    class Homsets(HomsetsCategory):
        def extra_super_categories(self) -> Sequence[Category]:
            return []

        class ParentMethods:
            def refined_homset_parent(self) -> int:
                return 2


class StandaloneHomCategory(LocalHomsetsBase):
    def super_categories(self) -> list[object]:
        return [Objects()]

    class ParentMethods:
        def local_hom_parent(self) -> int:
            return 1

    class ElementMethods:
        def local_hom_element(self) -> int:
            return 2

    Endset = cast(
        Any,
        LazyImport(
            "tests.fixtures.invariant_core.provider_roles.homsets",
            "LocalEndHomCategory",
        ),
    )


class LocalEndHomCategory(CategoryWithAxiom_singleton):
    _base_category_class_and_axiom = (StandaloneHomCategory, "Endset")

    def extra_super_categories(self) -> Sequence[Category]:
        return [_sage_homsets_endset()]

    class ParentMethods:
        def local_end_hom_parent(self) -> int:
            return 3

    class ElementMethods:
        def local_end_hom_element(self) -> int:
            return 4

    Finite = cast(
        Any,
        LazyImport(
            "tests.fixtures.invariant_core.provider_roles.homsets",
            "LocalFiniteEndHomCategory",
        ),
    )


class LocalFiniteEndHomCategory(CategoryWithAxiom_singleton):
    _base_category_class_and_axiom = (LocalEndHomCategory, "Finite")

    def extra_super_categories(self) -> Sequence[Category]:
        return [LocalEndHomCategory()]

    class ParentMethods:
        def local_finite_end_hom_parent(self) -> int:
            return 5

    class ElementMethods:
        def local_finite_end_hom_element(self) -> int:
            return 6
