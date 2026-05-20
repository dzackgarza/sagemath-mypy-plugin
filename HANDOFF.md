# HANDOFF.md — sage-mypy-category-plugin

## Current branch: `rewrite/invariant-core`

All phases from `finishing-work.md` in the vault are complete as of commit `b8d9a39`.
186 tests pass across all 7 suites.

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

### Open items

The PR (`rewrite/invariant-core` → `main`) has received Gemini code review.
All HIGH priority comments have been addressed. All MEDIUM priority comments have been
addressed: two were already fixed, one required `_returns_typing_self` to handle
`typing_extensions.Self` (commit `5af2f81`), two were architectural explanations.

The consumer `just consumer-mypy` run produces 1219 errors in 165 files — these are
real mypy type errors in the `category_specs` consumer codebase, not plugin errors.
The plugin is not responsible for fixing consumer code type errors.
