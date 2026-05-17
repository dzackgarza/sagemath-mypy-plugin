# GOALS.md — sage-mypy-category-plugin

## Mission

Mypy must **completely understand** Sage's dynamic category system.

The plugin's job is to give mypy true knowledge of Sage's runtime semantics so
that every mypy error code fires only when there is a genuine type error — not
when mypy is simply blind to Sage's dynamic construction patterns.

"Exit 0" is a side effect of correctness, not the goal. The goal is that mypy's
internal type model reflects Sage's real type relationships.

## Architectural Principle

**Suppression is never a permanent solution.**

Suppressing an error code (removing it from mypy's error map without teaching
mypy the truth) is explicitly a stopgap. It must be:

- Documented with the suppression site and the target resolution path.
- Paired with a test that proves the error fires without the plugin.
- Replaced with a teaching implementation as soon as mypy's plugin API supports
  the necessary mechanism.

Why: suppression silences a mypy error, which is *potentially useful static
checking data* for downstream users. A suppressed `[assignment]` on a method
container redefinition could mask a genuine covariance violation in user code.
The plugin must not be an "ignore file by another name."

## Resolution Hierarchy

When approaching a Sage pattern that mypy cannot currently type-check, apply
these strategies in order:

### 1. Teach mypy the truth (preferred)

Give mypy the type information it needs to reach the correct conclusion on its
own. Examples:

- **Injecting TypeInfos into `info.mro`** so `@override` walks the true
  category hierarchy (already done for `@override`).
- **Declaring method container types as covariant** in their MRO relationship
  so that `SubCategory.ParentMethods` is recognized as a subtype of
  `BaseCategory.ParentMethods`.
- **Injecting dunder methods** (`__contains__`, `__ne__`) into method container
  TypeInfos so that operator resolution works for `ElementMethods` and
  `SubcategoryMethods`.
- **Injecting attributes** (`_with_axiom`) into method container TypeInfos.
- **Using `get_method_hook` / `get_function_hook`** to teach mypy about
  Sage-specific decorators and dispatch patterns.
- **Stub files (`.pyi`):** Typed signatures for Sage functions/classes that are
  untyped at runtime (e.g. `@cached_method`, `@abstract_method`,
  `Category`, `CategoryWithAxiom`, `Constructors`, `FunctorialConstructionCategory`).

### 2. Sage-aware dispatch hooks

When mypy's type system fundamentally cannot model a Sage pattern, use plugin
hooks that *narrow mypy's behavior* to match Sage's semantics rather than
broadly suppressing error codes. Example:

- **`__classcall_private__` dispatch**: Teach mypy that when
  `SomeCategory(args)` is called, the actual `__init__` signature may be
  modified by `__classcall_private__`. A hook should surface the effective
  call signature rather than silencing `[call-arg]` wholesale.

### 3. Suppression with documentation and migration path (last resort)

Only when mypy's plugin API genuinely cannot express the needed type
relationship AND there is no stub-based workaround. Every suppression must:

- Be scoped as narrowly as possible (specific file+line, not whole error code).
- Have a docstring explaining *what truth mypy is missing* and *what API change
  would make suppression unnecessary*.
- Be tracked in this document's Suppression Registry below.
- Be paired with a TDD conjunction test that proves the error fires without the
  plugin.

## Suppression Registry

Every active suppression in the codebase must be listed here.

### `_filter_postbind_method_assign_errors`

- **File**: `sage_mypy_category_plugin/plugin.py`, line 525
- **Suppresses**: `[assignment]` and "Cannot assign to a method" on postbind
  method container aliases (e.g. `Category.ParentMethods = SomeHelper`).
- **What mypy doesn't know**: That `ParentMethods = SomeAlias` is a valid
  covariant re-assignment of a method container class attribute — Sage's
  category hierarchy guarantees that `SomeAlias` is a subtype of the original
  `ParentMethods`.
- **Target resolution**: Teach mypy that method container class attributes are
  covariant. Inject the subtype relationship into `info.mro` or use
  `get_attribute_hook` to surface the correct type.
- **Migration path**: Implement method-container covariance tracking, then
  remove `_filter_postbind_method_assign_errors`. The covariant assignment
  test (`test_covariant_container_assignment`) is the RED test for this.

### `_filter_bound_helper_non_method_errors`

- **File**: `sage_mypy_category_plugin/plugin.py`, line 505
- **Suppresses**: `@final cannot be used with non-method functions` and
  `"abstractmethod" used with a non-method` on helper alias assignments.
- **What mypy doesn't know**: That `ParentMethods.f = final_alias` is
  semantically a method binding — the alias carries `@final`/`@abstractmethod`
  semantics that apply to the target method.
- **Target resolution**: Teach mypy that the target of a helper alias binding
  IS a method, not a module-level function. Apply the decorator semantics
  (`is_final`, `abstract_status`) to the target Var rather than the alias.
  The `_copy_helper_flags` function partially does this already for some cases;
  the suppression handles the remaining error-site filtering.
- **Migration path**: Complete `_copy_helper_flags` coverage for all decorator
  semantics so mypy doesn't fire the error in the first place. Remove the
  suppression.

## Test Surface State

All surfaces are tested with the conjunction pattern:
`(plugin on/off) × (valid/invalid usage)` asserting on mypy exit code and
error output.

| Surface | Status | Resolution path |
|---|---|---|
| `ParentMethods @override` | GREEN | MRO injection (teach) |
| `ElementMethods @override` | GREEN | MRO injection (teach) |
| `SubcategoryMethods @override` | not yet tested | MRO injection (teach) |
| `MorphismMethods @override` | not yet tested | MRO injection (teach) |
| `@cached_method` decorator typing | RED | Stub for `cached_method` (teach — preserve return type) |
| `Constructors()` zero-arg | RED | Hook to resolve instance method vs class (teach) |
| `FunctorialConstructionCategory()` zero-arg | RED | `__classcall_private__` dispatch hook (teach) |
| Construction selector class attribute | GREEN | Materialize category construction class attributes as zero-arg selector methods (teach) |
| Construction extra-super method containers | GREEN | Sage-native projection: parameterized construction categories instantiate through their owner category, then `super_categories()`/`parent_class.__bases__` contributes base-category `ParentMethods`/`ElementMethods` |
| `__classcall_private__` kwargs | RED | `__classcall_private__` dispatch hook (teach) |
| Operator `__contains__`/`__ne__` | RED | Inject dunders into TypeInfo (teach) |
| Covariant return narrowing | RED | Declare subtype in MRO (teach) |
| Value-dependent completion self return | GREEN | Declare self-return result container in MRO (teach) |
| `_with_axiom` attribute | RED | Inject attribute into TypeInfo (teach) |
| Covariant container assignment | RED | Declare method container covariance (teach) |
| Postbind assignment (helper aliases) | SUPPRESSED | Replace with covariance teaching (see registry) |
| Helper non-method decorator errors | SUPPRESSED | Complete `_copy_helper_flags` (see registry) |

## Non-Goals

- **Completing the Sage stub package.** The bundled `sage-stubs/` is a narrow
  interop layer covering only the interfaces this plugin consumes directly. A
  comprehensive Sage type-stub package is out of scope.
- **Type-checking Sage's own source code.** The plugin targets downstream
  consumers of Sage's category system (e.g. `category_specs/`), not Sage's
  internal Python implementation.
- **Runtime type enforcement.** The plugin is static-analysis only. It does
  not modify Sage's runtime behavior.
