"""CategoryWithAxiom subclasses are validly called with zero arguments.

In Sage, CategoryWithAxiom.__classcall__ intercepts Foo() and routes it to
base_category_class()._with_axiom(axiom), supplying base_category internally.
The public constructor never requires base_category to be passed explicitly.

This mirrors the real failure pattern (~44 errors) in:
  category_specs/rings/subcategories/field.py:58  (_CommutativeRings())
  category_specs/rings/subcategories/commutative.py  (_IntegralDomains())
  category_specs/topological_spaces/subcategories/metric.py  (TopologicalSpaces())
  etc.

The entire Sage category hierarchy follows this pattern:
  Rings(CategoryWithAxiom)  ->  _base_category_class_and_axiom = (Rngs, "Unital")
  Rngs(CategoryWithAxiom)   ->  _base_category_class_and_axiom = (..., "AdditiveInverse")
so Rings() with no arguments is always valid.
"""

from __future__ import annotations

from sage.categories.category_with_axiom import CategoryWithAxiom
from sage.categories.category import Category


class _BaseAxiomCategory(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()


class _RefinedAxiomCategory(CategoryWithAxiom):
    _base_category_class_and_axiom = (_BaseAxiomCategory, "Refined")

    def super_categories(self):
        return [_BaseAxiomCategory.an_instance()]


class _DoublyRefinedAxiomCategory(CategoryWithAxiom):
    _base_category_class_and_axiom = (_RefinedAxiomCategory, "DoublyRefined")

    def super_categories(self):
        # Zero-argument call to a CategoryWithAxiom subclass — must not fire
        # [call-arg] "Missing positional argument 'base_category'".
        return [_RefinedAxiomCategory()]


class _UserOfAxiomCategories(Category):
    def super_categories(self):
        # Both zero-argument calls must be accepted.
        return [
            _RefinedAxiomCategory(),
            _DoublyRefinedAxiomCategory(),
        ]
