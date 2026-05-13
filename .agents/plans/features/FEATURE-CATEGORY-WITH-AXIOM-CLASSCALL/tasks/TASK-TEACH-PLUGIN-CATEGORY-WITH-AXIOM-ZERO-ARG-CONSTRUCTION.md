---
id: TASK-TEACH-PLUGIN-CATEGORY-WITH-AXIOM-ZERO-ARG-CONSTRUCTION
trackerStatus:
  type: task
parents:
- '[[FEATURE-CATEGORY-WITH-AXIOM-CLASSCALL]]'
dependsOn: []
title: Teach plugin that CategoryWithAxiom subclasses are validly called with zero arguments
status: unstarted
priority: high
activityType: implementation
---
# Task: Teach Plugin That CategoryWithAxiom Subclasses Are Validly Called With Zero Arguments

## Summary

~44 `[call-arg]` errors of the form:

```
Missing positional argument "base_category" in call to "_CommutativeRings"
Missing positional argument "base_category" in call to "TopologicalSpaces"
Missing positional argument "base_category" in call to "_Fields"
...
```

These are false positives. Every `CategoryWithAxiom` subclass in Sage is designed to
be called with zero arguments. mypy sees `__init__(self, base_category: SageCategory)`
and incorrectly concludes `base_category` is a required public argument.

## How Sage Actually Works

Every `CategoryWithAxiom` subclass defines `__classcall__` (inherited from
`CategoryWithAxiom`, defined in
`sage/categories/category_with_axiom.py:1978`):

```python
def __classcall__(cls, *args, **options):
    (base_category_class, axiom) = cls._base_category_class_and_axiom
    if len(args) == 1 and not options and isinstance(args[0], base_category_class):
        return super().__classcall__(cls, args[0])
    else:
        return base_category_class(*args, **options)._with_axiom(axiom)
```

When called with zero arguments (e.g. `CommutativeRings()`), the `else` branch fires:
it constructs the base category (`Rings()`) and applies the axiom
(`._with_axiom("Commutative")`), supplying `base_category` internally. The
`__init__(self, base_category)` is never called directly by user code.

This pattern is recursive: `Rings` itself is a `CategoryWithAxiom` of `Rngs` with
axiom `"Unital"` (`_base_category_class_and_axiom = (Rngs, "Unital")`), and `Rngs`
is a `CategoryWithAxiom` of `MagmasAndAdditiveMagmas.Distributive...` with axiom
`"AdditiveInverse"`. Every level of the hierarchy uses the same zero-argument
`__classcall__` routing. `base_category` is never a public constructor argument at
any level.

## Relevant Sage Source

- `sage/categories/category_with_axiom.py:1978` — `CategoryWithAxiom.__classcall__`
- `sage/categories/commutative_rings.py:21` — `class CommutativeRings(CategoryWithAxiom)`
  (no `__init__`, no `_base_category_class_and_axiom` needed — inherits from `Rings`)
- `sage/categories/rings.py:27` — `class Rings(CategoryWithAxiom)`,
  `_base_category_class_and_axiom = (Rngs, "Unital")`
- `sage/categories/rngs.py:19` — `class Rngs(CategoryWithAxiom)`,
  `_base_category_class_and_axiom = (MagmasAndAdditiveMagmas...Associative, "AdditiveInverse")`

## Required Fix

The plugin should recognise that any class inheriting from `CategoryWithAxiom` (or
`CategoryWithAxiom_singleton`, `CategoryWithAxiom_over_base_ring`) has a valid
zero-argument public constructor, regardless of what `__init__` declares. Concretely:

- When mypy checks a call site `Foo()` and `Foo` is a `CategoryWithAxiom` subclass,
  suppress `[call-arg]` for missing `base_category`.
- The plugin already identifies category classes via the dynamic inheritance graph;
  extend that identification to cover `CategoryWithAxiom` subclasses specifically.

## Affected Call Sites

All `[call-arg]` errors of the form `Missing positional argument "base_category" in
call to "X"` where `X` is a `CategoryWithAxiom` subclass. Currently ~44 errors across:

- `category_specs/homsets/autsets.py`
- `category_specs/homsets/endsets.py`
- `category_specs/rings/subcategories/` (commutative, field, integral_domain,
  number_field, global_field, gcd_domain, dedekind_domain, integrally_closed_domain,
  local, noetherian, reduced, algebraically_closed_field, local_field, discrete_valuation_ring)
- `category_specs/sets/__init__.py`
- `category_specs/sets/subcategories/real_set.py`
- `category_specs/topological_spaces/subcategories/`
- `category_specs/modules/__init__.py`
- `category_specs/lattices/__init__.py`
- `category_specs/forms/__init__.py`
- `category_specs/posets/subcategories/finite_lattice.py`
