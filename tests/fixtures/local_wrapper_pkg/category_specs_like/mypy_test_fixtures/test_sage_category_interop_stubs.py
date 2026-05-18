"""Bundled Sage category interop stubs cover consumed category helpers."""
from typing import final, override

from sage.categories.category import Category, CategoryWithParameters, JoinCategory
from sage.categories.category_with_axiom import (
    CategoryWithAxiom,
    CategoryWithAxiom_over_base_ring,
    CategoryWithAxiom_singleton,
)
from sage.categories.cartesian_product import CartesianProductsCategory
from sage.categories.homsets import HomsetsCategory, HomsetsOf
from sage.structure.category_object import CategoryObject
from sage.structure.parent import Parent


def category_helpers(category: Category) -> object:
    category._with_axiom("Finite")
    category.Constructors()
    category.base_category()
    return category.parent_class


def category_base_category(category: Category) -> Category:
    return category.base_category()


def category_object_helpers(obj: object, category: Category) -> None:
    CategoryObject._init_category_(obj, category)


def parent_init(obj: object) -> None:
    Parent.__init__(obj, category=None)


def category_classcall_helpers(category_type: type[Category], value: object) -> object:
    category_type._set_classcall(value)
    return category_type.__classcall__(category_type)


def category_with_axiom_constructor(category: Category) -> CategoryWithAxiom:
    return CategoryWithAxiom(category)


def cartesian_product_category(category: Category) -> Category:
    return CartesianProductsCategory.category_of(category)


class ParentHomMixin:
    @final
    def Hom(self, codomain: Category) -> object:
        return Parent.Hom(self, codomain)


class ParentHomObject(ParentHomMixin, Parent): ...


class CategoryWithAxiomOverrides(CategoryWithAxiom):
    @override
    def ambient_category(self) -> Category:
        return self.base_category()

    @override
    def defining_predicates(self) -> tuple[str, ...]:
        return ("is_example",)

    @override
    def defining_predicate(self, candidate: object) -> bool:
        return bool(candidate)


class CategoryExtraSuper(Category):
    @override
    def extra_super_categories(self) -> list[Category]:
        return []


class CategorySuperChild(Category): ...


class CategorySuperSpecific(Category):
    @override
    def super_categories(self) -> list[CategorySuperChild]:
        return []


def imported_category_bases(
    parameterized: CategoryWithParameters,
    axiom: CategoryWithAxiom,
    axiom_over_base_ring: CategoryWithAxiom_over_base_ring,
    axiom_singleton: CategoryWithAxiom_singleton,
    join_category: JoinCategory,
    homsets_category: HomsetsCategory,
    homsets_of: HomsetsOf,
) -> tuple[Category, ...]:
    return (
        parameterized,
        axiom,
        axiom_over_base_ring,
        axiom_singleton,
        join_category,
        homsets_category,
        homsets_of,
    )
