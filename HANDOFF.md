# HANDOFF.md — sage-mypy-category-plugin

## Current branch: `rewrite/invariant-core`

All phases from `finishing-work.md` in the vault are complete as of commit `b8d9a39`.
216 tests pass across all 7 suites (as of `a14e40a`).

### Phase completion status

| Phase | Description | Status |
| --- | --- | --- |
| 0 | Freeze core contract (CONTRACT.md, sentinels) | Done |
| 1 | Plugin-owned generation (`_generate_and_cache`, cache reuse) | Done |
| 2 | Projection structural tests (TypeInfo.bases/mro assertions) | Done |
| 3 | Real mathematical category fixtures (`tests/real_categories/`) | Done |
| 4 | Decorator behavior matrix on real categories | Done |
| 5 | Axioms, linked axioms, functorial, parameterized, homsets, morphisms (5A-5G) | Done |
| 6 | Generated stubs under plugin ownership | Done |
| 7 | Consumer end-to-end proof (E1-E6) | Done |
| 8 | Mutation and anti-reward-hacking suite | Done |
| 9 | Correctness argument and maintainability proof (`SPEC.md`) | Done |

### Phase 7 acceptance tests (all in `tests/test_plugin_projection.py`)

| Test | Maps to |
| --- | --- |
| `test_plugin_generates_manifest_from_packages_config` | E1: fresh run |
| `test_plugin_regenerates_from_clean_cache` | E1: idempotency |
| `test_plugin_reuses_cache_on_second_init_without_regenerating` | E2: cache hit |
| `test_plugin_detects_stale_source_and_regenerates_in_packages_mode` | E3: source mutation |
| `test_real_sage_category_behavior_matrix_uses_standard_mypy_rules` | E4: negative injection |
| `test_renamed_consumer_package_behavioral_invariant_holds` | E5: renamed-copy |
| `test_plugin_recovers_from_corrupt_cache_in_packages_mode` | E6: stale cache |

### Key Artifacts

- `CONTRACT.md` — formalized invariants I1-I7, banned patterns BP1-BP10, sentinel checklist
- `GOALS.md` — mission, architectural principle (suppression is never permanent), resolution hierarchy, Known Limitations, Test Surface State table
- `sage_mypy_category_plugin/plugin.py` — production plugin entry point
- `sage_mypy_category_plugin/oracle.py` — Sage runtime oracle (resolver subprocess context)
- `sage_mypy_category_plugin/resolver.py` — category discovery and manifest generation
- `sage_mypy_category_plugin/stubs.py` — generated stub writer

### Known Limitations (see GOALS.md for full detail)

Self-returning descriptors (`@classmethod`, `@staticmethod`, `@property`, `@cached_method`)
in external Sage runtime provider classes are not tracked in `ProviderMethodRecord` stubs.
Empirically, no Sage `@cached_method` in `ParentMethods` carries a `Self` annotation, so
no `@override` breakage occurs in practice. Migration path documented in GOALS.md.

### Test coverage additions (post-PR-open)

Coverage gaps closed in the `a05f047`–`a14e40a` commit range:

- `_validate_mypy_interval` both branches (inverted interval + current outside range)
- `_validate_projection_graph` duplicate unsupported providers, concrete parents, external
  source modules, provider methods
- `_validate_projection_graph` concrete parent cross-field coherence (all 7 cases)
- `_source_modules_stale_reason` file-missing and mtime_ns-mismatch branches
- `_normalize_role_name` full variant mapping contract
- `_returns_typing_self` actual `typing.Self` object form (Python ≥ 3.11)
- `ProviderMethodRecord._validate_method_signature` non-identifier names
- `import_module_and_qualname` / `import_fullname` boundary error paths
- `_generate_and_cache` "no categories found" error path
- `_parse_multiline_option` inline-comment stripping
- Plugin invalid role config error reporting

### Open items

The PR (`rewrite/invariant-core` → `main`) has received Gemini code review.
All HIGH priority comments have been addressed. All MEDIUM priority comments have been
addressed: two were already fixed, one required `_returns_typing_self` to handle
`typing_extensions.Self` (commit `5af2f81`), two were architectural explanations.

The consumer `just consumer-mypy` run produces 590 errors in 140 files (checked 260 source
files) — these are real mypy type errors in the `category_specs` consumer codebase exposed
by the plugin injecting Sage runtime MROs. The plugin is not responsible for fixing consumer
code type errors. Error breakdown (2026-05-21): `misc` 225, `attr-defined` 139, `arg-type`
57, `list-item` 44, `operator` 31, `override` 28, `return-value` 27, `call-arg` 19,
`type-var` 10, `assignment` 5, `return` 4, `index` 1. These correspond to the
`PHASE-QC-DYNAMIC-INHERITANCE-PLUGIN-REVIEW` task queue in the research repo.

**Passthrough mode** (commit `af7becf`): when `plugins = sage_mypy_category_plugin.plugin`
is listed in a mypy config but no `[sage-mypy-category-plugin]` section is present, the
plugin initializes in passthrough mode (no generation, no projection, no CompileError).
This makes global QC mypy configs that list the plugin generically work without errors.
CONTRACT invariant I4 is not violated: passthrough fires only when no config section is
present (and therefore no packages are configured), so there is no strict mode to enforce.
