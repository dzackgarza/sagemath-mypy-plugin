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

**Current branch (`rewrite/invariant-core`): no active suppressions.**

The invariant-core rewrite removed all diagnostic filter functions. The
`test_contract_no_diagnostic_filter_functions_in_plugin_package` sentinel in
`tests/test_automation_contract.py` enforces this: any `_filter*` function
added to the plugin package will fail CI.

Previous suppressions (`_filter_postbind_method_assign_errors`,
`_filter_bound_helper_non_method_errors`, `_filter_constructors_no_redef_errors`)
existed only on the `main` branch pre-rewrite. They are not present in this branch.

## Known Limitations

### Self-returning descriptors in sidecar/debug stubs

`ProviderMethodRecord` tracks only plain instance methods (`FunctionType`) that
return `Self`. Methods declared as `@classmethod`, `@staticmethod`, `@property`,
or Sage's `@cached_method` that also return `Self` are not captured in the
manifest and therefore are not explicitly typed in sidecar or debug-generated
runtime alias stubs.

**Descriptors affected**:

- `@classmethod`, `@staticmethod`, `@property` — not modelled as plain instance
  methods; the stub generator would need a `kind` field on `ProviderMethodRecord`
  to emit the correct decorator.
- `@cached_method` (Sage's `sage.misc.cachefunc.CachedMethod`) — a Cython
  `cdef class` whose `_cachedfunc` attribute is not exposed to Python.
  `_direct_provider_function_or_none` cannot inspect it without a fragile
  descriptor call (`member.__get__(sentinel, type).f`).  Empirically, Sage's own
  `@cached_method` members in external provider classes (e.g.
  `Sets.ParentMethods.an_element`) carry no `Self` return annotation, so they
  would pass through `_returns_typing_self` uncaptured regardless.

**Impact**: If a Sage external category's provider class declares a descriptor
method returning `Self`, and the installed Sage-version sidecar stub omits that
descriptor shape, mypy may not detect the override correctly from the sidecar.

**Scope**: Narrow. The sidecar stubs are only for external Sage runtime
providers, not for source-based provider classes (which mypy reads directly).
The structural MRO invariant is unaffected.  The `@override` behavior matrix
tests (including tests of `@classmethod`, `@staticmethod`, and `@property`
overrides) pass because those tests use source-based fixture providers, which
mypy reads directly rather than through stubs.

**Migration path**: Add a `kind` field to `ProviderMethodRecord` with values
`instance`, `classmethod`, `staticmethod`, `property`, `cached_method`. Extend
`_direct_provider_function_or_none` to unwrap these descriptors (for
`@cached_method`: call `member.__get__(sentinel, type(sentinel)).f`). Update
the stub generator to emit the appropriate decorator in the `.pyi` file.

## Test Surface State

All surfaces are tested with the conjunction matrix:
`(plugin on/off) × (valid/invalid usage)`.

| Surface | Status | Test |
|---|---|---|
| `ParentMethods @override` | GREEN | `test_behavior_matrix_uses_standard_mypy_inheritance_rules` |
| `ElementMethods @override` | GREEN | `test_non_parent_role_behavior_matrix_uses_standard_mypy_inheritance_rules` |
| `SubcategoryMethods @override` | GREEN | `test_non_parent_role_behavior_matrix_uses_standard_mypy_inheritance_rules` |
| `MorphismMethods @override` | GREEN | `test_non_parent_role_behavior_matrix_uses_standard_mypy_inheritance_rules` |
| `Homsets.ParentMethods @override` | GREEN | `test_non_parent_role_behavior_matrix_uses_standard_mypy_inheritance_rules` |
| `Homsets.ElementMethods @override` | GREEN | `test_non_parent_role_behavior_matrix_uses_standard_mypy_inheritance_rules` |
| Axiom category providers | GREEN | `test_local_axiom_behavior_matrix_uses_standard_mypy_rules`, `test_nested_sage_provider_behavior_matrix_uses_standard_mypy_rules` |
| Linked axiom categories | GREEN | `test_linked_axiom_projection_matches_sage_runtime_mro` |
| Functorial construction providers | GREEN | `test_nested_sage_provider_behavior_matrix_uses_standard_mypy_rules` |
| Parameterized category providers | GREEN | `test_nested_sage_provider_behavior_matrix_uses_standard_mypy_rules` |
| `@final` violation | GREEN | `test_real_sage_category_behavior_matrix_uses_standard_mypy_rules` |
| Override signature mismatch | GREEN | `test_real_sage_category_behavior_matrix_uses_standard_mypy_rules` |
| Consumer (renamed package) | GREEN | `test_renamed_consumer_package_behavioral_invariant_holds` |
| Mutation: ghost provider_bases | GREEN | `test_false_provider_base_reference_is_detected_by_plugin` |
| Mutation: ghost provider_mro | GREEN | `test_false_provider_mro_entry_is_detected_by_plugin` |
| Mutation: axiom provider_mro truncation/reordering | GREEN | `test_phase5A_nested_axiom_provider_mro_mutations_are_structurally_detectable` |
| Mutation: linked axiom provider_mro truncation/reordering | GREEN | `test_phase5B_linked_axiom_provider_mro_mutations_are_structurally_detectable` |
| Mutation: CartesianProducts provider_mro | GREEN | `test_phase5C_cartesian_products_provider_mro_mutations_are_structurally_detectable` |
| Mutation: TensorProducts provider_mro | GREEN | `test_phase5D_tensor_products_provider_mro_mutations_are_structurally_detectable` |
| Mutation: parameterized provider_mro | GREEN | `test_phase5E_parameterized_provider_mro_mutations_are_structurally_detectable` |
| Mutation: homset provider_mro | GREEN | `test_phase5F_homset_provider_mro_mutations_are_structurally_detectable` |
| Mutation: morphism provider_mro | GREEN | `test_phase5G_morphism_provider_mro_mutations_are_structurally_detectable` |
| Cache: fresh generation | GREEN | `test_plugin_generates_manifest_from_packages_config` |
| Cache: hit (no regeneration) | GREEN | `test_plugin_reuses_cache_on_second_init_without_regenerating` |
| Cache: stale source → regeneration | GREEN | `test_plugin_detects_stale_source_and_regenerates_in_packages_mode` |
| Cache: corrupt manifest → recovery | GREEN | `test_plugin_recovers_from_corrupt_cache_in_packages_mode` |
| Self-returning classmethods in stubs | KNOWN LIMITATION | See Known Limitations above |

## Non-Goals

- **Completing all Sage type stubs.** The sidecar `sage-stubs` package is a
  version-pinned interop layer for the Sage category/provider/interface modules
  needed by this plugin's projection manifests. A comprehensive Sage type-stub
  package remains out of scope.
- **Type-checking Sage's own source code.** The plugin targets downstream
  consumers of Sage's category system (e.g. `category_specs/`), not Sage's
  internal Python implementation.
- **Runtime type enforcement.** The plugin is static-analysis only. It does
  not modify Sage's runtime behavior.
