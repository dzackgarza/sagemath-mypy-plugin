# SPEC.md — sage-mypy-category-plugin correctness argument

This document gives the formal correctness argument for the plugin's MRO-projection
approach. It is the canonical reference for why the plugin works and why any proposed
change is safe or unsafe. CONTRACT.md governs invariants and banned patterns; this
document explains **why** those invariants suffice.

---

## Background: The Sage provider model

Sage category hierarchy is implemented at runtime through
`Category._make_named_class`. When a category `C` is instantiated, Sage creates
several *named classes* — one per provider role — by merging the corresponding
inner classes from `C`'s super-category chain:

| Role          | Runtime attribute   | Source inner class  |
|---------------|--------------------|--------------------|
| parent        | `parent_class`     | `ParentMethods`    |
| element       | `element_class`    | `ElementMethods`   |
| subcategory   | `subcategory_class`| `SubcategoryMethods`|
| morphism      | `morphism_class`   | `MorphismMethods`  |
| homset parent | `Homsets().parent_class` | `Homsets.ParentMethods` |
| homset element| `Homsets().element_class`| `Homsets.ElementMethods`|

The MRO of each named class is determined by Python's C3 linearisation of the
source inner classes in category MRO order. This MRO is not written anywhere in
the source — it is constructed dynamically each time a category is first imported.

Mypy cannot see this MRO. Without the plugin, every `@override` annotation on a
provider method fails with "no base method was found", every `@final` violation
is invisible, and every abstract-method obligation is undetected.

---

## Formal definitions

Let `C` be a Sage category class with `super_categories()` well-defined.  
Let `r` be a provider role from the set `{parent, element, subcategory, morphism, homset_parent, homset_element}`.

**K(C, r)**  
The Sage runtime named class for role `r` of category `C`.  
Concretely: `C().parent_class`, `C().element_class`, etc.  
This is the class constructed by `Category._make_named_class` at category instantiation.

**P(C, r)**  
The source provider class for role `r` of category `C`.  
Concretely: the body-only inner class `C.ParentMethods`, `C.ElementMethods`, etc.,
as visible in the Python source file defining `C`.

**π_r**  
The partial function from runtime named classes to source provider classes for role `r`.  
Defined by: π_r(`K`) = `P(C, r)` if `K` is `K(C, r)` for some `C`; undefined otherwise.

**provider_mro(P(C, r))**  
The sequence produced by the oracle:

```
provider_mro(P(C, r)) = [π_r(K) for K in K(C, r).__mro__ if π_r(K) is defined]
```

This is the image of the Sage runtime MRO under the projection `π_r`.

**The manifest**  
A validated `ProjectionManifest` (JSON) produced by `resolver.py` at plugin
initialisation. It records, for every discovered provider `P(C, r)`:

```
ProviderProjection(
    provider      = fullname(P(C, r)),
    provider_mro  = provider_mro(P(C, r)),
    provider_bases = direct-parent subset of provider_mro,
    runtime_class = fullname(K(C, r)),
    runtime_mro   = fullname(K) for K in K(C, r).__mro__,
    ...
)
```

**TypeInfo.mro(P)**  
The MRO that mypy uses for class `P` during semantic analysis. Without the plugin
this equals what the source declares directly. With the plugin it is rewritten by
`get_customize_class_mro_hook`.

---

## The correctness theorem

**Theorem.**  
Assume:

- **A1.** The manifest was generated from Sage runtime with the current source modules
  (source-digest parity enforced by `report_config_data`).
- **A2.** Every provider in `provider_mro` is visible to mypy: either as a source
  file under the configured packages, or as a Sage-version sidecar stub installed
  before mypy computes module search paths.
- **A3.** The plugin applies no diagnostic filtering and copies no method bodies.
- **A4.** The mypy version is within `[mypy_min_version, mypy_max_version]` declared
  in the manifest.
- **A5.** For every projected provider `P`, the plugin sets
  `TypeInfo.bases(P)` and `TypeInfo.mro(P)` to the manifest projection.

Then, for the standard mypy inheritance-sensitive checks — `@override`,
`@final`, abstract method obligations, override-signature compatibility,
property/classmethod/staticmethod inheritance, and overloads — mypy
analyses each provider class as if the Sage dynamic provider inheritance
had been statically declared in the source.

---

## Proof sketch

Mypy's inheritance checks are purely functions of two inputs:

1. The **TypeInfo graph** — specifically `TypeInfo.bases` and `TypeInfo.mro` for
   each class.
2. The **visible method definitions** — the `SymbolTable` entries accessible
   through that MRO.

*Step 1 (manifest fidelity, by A1).*  
The manifest field `provider_mro(P(C, r))` is the exact image of
`K(C, r).__mro__` under `π_r`, computed from live Sage runtime.  
By A1, the manifest is current: the plugin invalidates and regenerates the manifest
whenever `report_config_data` sees a source-digest mismatch.  
Therefore `provider_mro(P(C, r))` faithfully represents what Sage would produce for
the current source.

*Step 2 (TypeInfo graph correctness, by A5).*  
The hook `_customize_provider_mro` (plugin.py) executes exactly:

```python
info.bases = [Instance(base_info, []) for base_info in base_infos]
info.mro   = [*mro_infos, object_info]
```

where `base_infos` = TypeInfos for `projection.provider_bases` and
`mro_infos` = TypeInfos for `projection.provider_mro`.  
By A5 this is exactly the manifest projection.  
After the hook, mypy's TypeInfo graph for `P` equals the projection of Sage's runtime
named-class graph.

*Step 3 (symbol visibility, by A2).*  
Every TypeInfo in `provider_mro` must be reachable at analysis time.  
The plugin's `get_additional_deps` declares cross-module ordering edges so that
all base providers are analysed before their dependents.  
The installed `sage-stubs` sidecar makes Sage's external runtime providers
visible under stable module paths before plugin initialization.  
By A2, all TypeInfos are present; `_lookup_typeinfos` fails loud (via `ctx.api.fail`)
rather than silently returning `None` if any are missing — no silent fallback is
possible.

*Step 4 (no interference, by A3).*  
The plugin registers only:

- `get_customize_class_mro_hook` — rewrites TypeInfo graph
- `get_additional_deps` — declares ordering edges
- `report_config_data` — reports digest metadata

It does not register `get_function_hook`, `get_method_hook`, `get_attribute_hook`,
`get_base_class_hook`, or any other hook that could alter diagnostics or rewrite
method bodies.  
By A3, mypy's ordinary diagnostic logic runs unmodified on the corrected TypeInfo graph.

*Conclusion.*  
By steps 1–4, the TypeInfo graph presented to mypy's semantic analyser is exactly
the static representation of Sage's runtime provider hierarchy. Mypy's standard
inheritance checks therefore produce identical results to what they would produce
if a developer had hand-written all provider MRO declarations in the source.

---

## Why the manifest schema enforces correctness

The `ProjectionManifest` Pydantic model (manifest.py) enforces three graph invariants
that together prevent the plugin from projecting a graph that contradicts Sage runtime:

**Closed-world reference check** (`_validate_projection_graph`).  
Every provider name in any `provider_mro` or `provider_bases` field must itself be a
declared `ProviderProjection` entry. A manifest that references an undeclared provider
fails Pydantic validation at load time, before the plugin hook runs. This prevents
injecting synthetic bases that were not resolved from Sage runtime.

**MRO-bases subset check** (per-projection).  
`provider_bases ⊆ provider_mro[1:]` is checked per projection. A manifest with
a base that does not appear in the MRO is rejected. This mirrors the C3 invariant
that direct bases appear in the linearisation.

**Source-digest parity** (`report_config_data`).  
The manifest records the SHA-256 and mtime of every source module. Mypy's
`report_config_data` mechanism re-runs the plugin whenever config data changes.
The plugin re-generates the manifest when source digests do not match the
manifested values, keeping A1 true across incremental builds.

---

## What breaks each assumption

| Assumption | If violated... |
|------------|---------------|
| A1 (manifest current) | Provider MRO in manifest diverges from Sage runtime. `@override` annotations that were valid become invisible or phantom. Source-digest parity check catches this on the next mypy run. |
| A2 (symbols visible) | `_lookup_typeinfos` calls `ctx.api.fail`, emitting a "references missing symbols" error. The projection is not applied; the class retains its source-declared MRO, causing downstream `@override` failures. |
| A3 (no interference) | Any added hook that rewrites diagnostics creates a second semantic engine inconsistent with the TypeInfo projection. The proof no longer applies and correctness is unverifiable. This is why CONTRACT.md §BP7 bans broad hooks without justification. |
| A4 (mypy version) | Mypy may change how it consumes `TypeInfo.bases`/`.mro`. The `mypy_min_version`/`mypy_max_version` bounds in the manifest make stale-mypy failures diagnosable rather than silent. |
| A5 (plugin applied) | Only possible if `get_customize_class_mro_hook` returns `None` for a provider. The hook returns `None` iff the fullname is not in `_projection_by_provider`. Since the manifest is the source of `_projection_by_provider`, a provider absent from the manifest is silently left at its source-declared MRO (which has no bases). In strict mode this must produce a diagnostic; see CONTRACT.md §I4. |

---

## Implementation references

| Proof step | Implementation artifact |
|------------|------------------------|
| Runtime MRO oracle | `oracle.py:provider_projections_for_categories` |
| Projection computation | `oracle.py:_provider_projection_for_named_class_trace` |
| Manifest schema invariants | `manifest.py:ProjectionManifest._validate_projection_graph` |
| Source-digest parity | `plugin.py:report_config_data` → manifest regeneration |
| TypeInfo graph rewrite | `plugin.py:_customize_provider_mro` |
| Fail-loud lookup | `plugin.py:_lookup_typeinfos` |
| Symbol ordering edges | `plugin.py:get_additional_deps` |
| Upstream Sage provider visibility | installed Sage-version `sage-stubs` sidecar |
| Debug/runtime alias stub generation | `stubs.py` + `plugin.py:_generate_and_write_stubs` |
| Manifest validation tests | `tests/test_manifest.py` |
| Structural MRO invariant tests | `tests/test_plugin_projection.py` |
| Behavior matrix tests | `tests/test_behavior_matrix.py` |
| Mutation tests (proof of no silent fallback) | `tests/test_behavior_matrix.py::test_false_provider_*` |
| Banned-pattern sentinel tests | `tests/test_automation_contract.py` |

---

## This proof is why broad hooks are banned

Every additional hook (`get_function_hook`, `get_method_hook`, etc.) would create a
second semantic engine operating in parallel with mypy's ordinary logic. The interaction
between the rewritten TypeInfo graph and a second hook is not captured by this proof.
Introducing such hooks requires a fresh correctness argument that explains the joint
behaviour. CONTRACT.md §BP7 enforces this by requiring explicit justification in the
Suppression Registry for any hook outside the allowed three.
