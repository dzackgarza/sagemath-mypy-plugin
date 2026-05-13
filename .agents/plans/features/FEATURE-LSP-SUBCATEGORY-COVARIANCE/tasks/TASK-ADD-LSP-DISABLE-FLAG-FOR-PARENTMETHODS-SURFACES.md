---
id: TASK-ADD-LSP-DISABLE-FLAG-FOR-PARENTMETHODS-SURFACES
trackerStatus:
  type: task
parents:
- '[[FEATURE-LSP-SUBCATEGORY-COVARIANCE]]'
dependsOn: []
title: Add flag to disable LSP enforcement on ParentMethods/ElementMethods surfaces
status: unstarted
priority: high
activityType: implementation
---
# Task: Add Flag to Disable LSP Enforcement on ParentMethods/ElementMethods Surfaces

## Summary

The plugin currently surfaces `[assignment]` Liskov Substitution Principle violations
on `ParentMethods`, `ElementMethods`, and `MorphismMethods` class attribute assignments
in subcategory homset classes. These are false positives: LSP does not apply to
category-theoretic method refinement.

## Mathematical Justification

A method on `ParentMethods` is typically a functor F: A → B where A is the category.
For example, `cardinality` is a functor F: **Sets** → ℕ ∪ {∞}.

When refining to a subcategory, e.g. `EvenCardinalitySets`, one may define
F': EvenCardinalitySets → 2ℕ by restriction — both the domain and codomain become
more specific. This is **covariant in both input and output**.

LSP requires preconditions to be weakened (contravariant in inputs) in subtypes. But
here, the input domain is NARROWED intentionally — F' is defined on a SMALLER domain
by design, and is NOT expected to be usable wherever F is. Most functors defined on
small or structured subcategories are completely undefinable on larger, less structured
categories. Subcategories exist precisely to provide non-generalizable implementations.

Concretely: if F: A → B and F': A' → B' with A' ≤ A and B' ≤ B, we do NOT expect F'
to substitute for F. F' is defined on a strictly smaller domain. This is the entire
point of subcategory refinement.

Therefore, assigning a more specific `ParentMethods` class to a subcategory homset is
mathematically correct and should not be flagged as a Liskov violation.

## Observed Errors

The plugin currently causes ~31 `[assignment]` errors of the form:

```
category_specs/cat/homsets.py:126: error: Incompatible types in assignment
  (expression has type "type[_CatHomCategoryObjectMethods]",
   base class "HomCategoryOf" defined the type as "type[ParentMethods]")
  [assignment]
```

These appear across all homset files:
- `cat/homsets.py`
- `sets/homsets.py`
- `modules/homsets.py`
- `rings/homsets.py`
- `lattices/homsets.py`
- `posets/homsets.py`
- `topological_spaces/homsets.py`
- `algebras/homsets.py`

## Required Change

Add a mechanism — either a plugin config flag or an automatic rule — to suppress
`[assignment]` on class attribute assignments where:

- The attribute name is `ParentMethods`, `ElementMethods`, or `MorphismMethods`
- The assignment occurs in a class that the plugin has identified as a category
  or homset class (i.e., within the dynamic inheritance graph)

The suppression should be principled: the plugin knows the dynamic inheritance graph
and knows these assignments are category-theoretic refinements, not OOP substitutions.

## Acceptance Criteria

- All `[assignment]` errors on `ParentMethods`/`ElementMethods`/`MorphismMethods`
  assignments in category/homset classes are suppressed.
- No `# type: ignore` is required in the spec code.
- The suppression is documented in the plugin with reference to the mathematical
  justification above.
- Non-category class attribute assignments continue to be checked normally.
