from __future__ import annotations

from typing import Any, cast, final

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.category_singleton import Category_singleton  # type: ignore[import-untyped]
from sage.categories.homsets import Homsets as SageHomsets  # type: ignore[import-untyped]
from sage.categories.homsets import HomsetsCategory  # type: ignore[import-untyped]
from sage.categories.objects import Objects  # type: ignore[import-untyped]
from sage.misc.constant_function import ConstantFunction  # type: ignore[import-untyped]
from sage.structure.dynamic_class import DynamicMetaclass  # type: ignore[import-untyped]

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class TopCategory(LocalCategoryBase):
    def super_categories(self) -> list[object]:
        return [Objects()]

    class Homsets(HomsetsCategory):
        def extra_super_categories(self) -> list[object]:
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
        def extra_super_categories(self) -> list[object]:
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


class StandaloneHomCategory(LocalHomsetsBase):
    def super_categories(self) -> list[object]:
        return [Objects()]

    class ParentMethods:
        def local_hom_parent(self) -> int:
            return 1

    class ElementMethods:
        def local_hom_element(self) -> int:
            return 2
