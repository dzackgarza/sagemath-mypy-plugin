# HANDOFF.md — sage-mypy-category-plugin

## Current State

The repository is moving from the transitional generated-stub architecture to
the vault-defined final architecture:

```text
install sage-mypy-category-plugin
install Sage-version sage-stubs sidecar
configure packages / roles / cache_dir / strict
run sage -python -m mypy
```

The plugin owns projection-manifest generation and cache refresh. Upstream Sage
provider visibility belongs to the installed `sage-stubs` sidecar. Normal
production usage must not require generated upstream Sage stubs, pre-generated
manifests, wrapper recipes, `MYPYPATH`, `cache_dir/stubs` in `mypy_path`,
diagnostic filtering, namespace hardcoding, or consumer error-count targets.

## Canonical Success Metric

For every configured Sage category `C` and provider role `r`, let `K(C, r)` be
the runtime named class Sage constructs and `P(C, r)` the corresponding source
provider class. Completion requires this chain of evidence:

```text
Sage runtime constructs K(C, r)
manifest records K.__bases__ and K.__mro__
manifest records projection_r(K.__bases__) and projection_r(K.__mro__)
mypy semantic analysis sets TypeInfo(P).bases to projected provider_bases
mypy semantic analysis sets TypeInfo(P).mro to projected provider_mro + object
```

Behavior tests are supporting evidence only when the structural TypeInfo
invariant holds. A clean or smaller consumer error count is not proof.

## Solid Evidence

- `README.md`, `CONTRACT.md`, `SPEC.md`, and `GOALS.md` describe the sidecar
  architecture and the structural TypeInfo invariant.
- `tests/test_production_lifecycle.py` shells out through plain
  `sage -python -m mypy` with plugin config and no `cache_dir/stubs` path.
- `tests/test_plugin_projection.py` contains structural TypeInfo
  `bases`/`mro` assertions against manifest projections.
- `tests/test_behavior_matrix.py` and `tests/test_role_behavior_matrix.py`
  contain plugin on/off × valid/invalid behavior matrices.
- `just consumer-structural` runs a retained structural canary against the real
  `/home/dzack/research/category_specs` tree and compares representative
  provider `TypeInfo.bases`/`mro` values to the plugin-generated manifest.
- The nested `sage-stubs/` sidecar repository contains Sage 10.7 provider and
  interface shells used by real fixtures and `category_specs` projections.

## Remaining Release Gates

- Remove or demote all production-facing wrapper/debug-stub surfaces. In
  particular, `consumer-mypy`, `write_consumer_config`, and first-class
  generated-upstream-stub validation must not remain release evidence.
- Keep debug manifest and runtime-alias paths out of production acceptance.
  They may exist only as explicitly non-production diagnostics.
- Expand real `/home/dzack/research/category_specs` evidence beyond the current
  retained canary where needed: negative injected consumer errors, broader
  provider role coverage, and missing TypeInfo/projection triage.
- Keep production lifecycle tests in the default and release validation matrix.
- Run the contract sentinel greps, focused production/structural/behavior tests,
  mutation checks, sidecar visibility checks, and `just release-check`.

## Do Not Use As Proof

- Total mypy error counts from `category_specs`.
- A generated manifest supplied through `manifest = ...`.
- A wrapper that writes a temporary config before invoking mypy.
- A generated `cache_dir/stubs` tree used for upstream Sage provider visibility.
- Tests that pass only because generated stubs or `_sage_category_types` make
  symbols visible outside the sidecar/source path contract.
