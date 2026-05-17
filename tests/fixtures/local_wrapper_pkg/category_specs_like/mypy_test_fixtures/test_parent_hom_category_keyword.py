"""Parent.Hom accepts Sage's unbound category keyword call."""
from sage.categories.category import Category
from sage.structure.category_object import CategoryObject
from sage.structure.parent import Parent


def parent_hom_with_category(
    domain: CategoryObject,
    codomain: CategoryObject,
    category: Category,
) -> object:
    return Parent.Hom(domain, codomain, category=category)
