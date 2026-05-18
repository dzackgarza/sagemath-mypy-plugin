# Invariant-Core Rewrite Plan

## Defect Statement

The existing implementation accumulated a second semantic engine inside the
mypy plugin: source/AST discovery, receiver inference, constructor hooks,
diagnostic filtering, narrow stubs, and fallback paths. That code can reduce a
consumer error count without proving that mypy's internal type model matches
Sage's runtime category model.

The rewrite target is narrower and falsifiable:

```text
For every method-provider class handled by the plugin:

    mypy TypeInfo MRO
    ==
    Sage runtime named-class MRO projected back to provider classes
```

Decorator behavior is downstream of that invariant. If the invariant holds,
`@override`, `@final`, signature override checks, abstract methods, properties,
and overloads should be checked by mypy's ordinary inheritance machinery.

## Canonical Sources

- `AGENTS.md` defines the repository contract, banned patterns, and required
  plugin-owned test surface.
- `GOALS.md` records current known surfaces and explicitly states that
  suppression is not a permanent solution.
- `/home/dzack/vault/projects/sagemath-mypy-plugin/Mypy Plugin for Sage.md`
  is the pivot critique: stop local error-chasing and make Sage runtime
  projection the executable invariant.
- Sage runtime is the semantic oracle for category named classes, bases, and
  MRO order.
- Mypy is the checking engine. The plugin must teach mypy inheritance facts,
  not reimplement decorator or override rules.

## Hard Constraints

- No legacy implementation is copied forward without a new failing structural
  test.
- No source-AST fallback for category semantics in the core.
- No diagnostic filtering in the core.
- No receiver-self inference in the core.
- No constructor, method, function, or attribute hooks in the core except where
  needed for manifest loading, MRO projection, dependency ordering, and cache
  invalidation.
- No broad Sage stub package in the core. Stubs may be added only when a test
  proves a narrow interop boundary owned by this repository.
- No plugin-on success-only tests. Behavioral tests use the conjunction
  pattern from `AGENTS.md`.
- No consumer-error-count objective. Consumer runs are evidence-gathering only
  until a structural invariant covers the relevant shape.

## Target Package Shape

```text
sage_mypy_category_plugin/
    __init__.py
    manifest.py
    oracle.py
    plugin.py

tests/
    fixtures/
        invariant_core/
            diamond_runtime.py
            diamond_behavior_valid.py
            diamond_behavior_invalid.py
            diamond_behavior_final_violation.py
            diamond_behavior_signature_mismatch.py
    test_manifest.py
    test_oracle_projection.py
    test_plugin_projection.py
    test_behavior_matrix.py
```

The initial rewrite should delete or archive the old implementation, old tests,
old stubs, and tracked pycache from the branch before introducing the new core.
The retained docs are guidance and evidence, not proof of completion.

## Runtime Oracle Contract

`oracle.py` owns the Sage-runtime projection. It runs under Sage Python and
does not depend on mypy internals.

Core data model:

```python
from dataclasses import dataclass
from typing import Literal

ProviderRole = Literal["parent", "element", "subcategory", "morphism"]

@dataclass(frozen=True)
class ProviderProjection:
    provider: str
    role: ProviderRole
    runtime_class: str
    runtime_bases: tuple[str, ...]
    runtime_mro: tuple[str, ...]
    provider_bases: tuple[str, ...]
    provider_mro: tuple[str, ...]
```

The first implementation may use explicit category class names supplied by a
test fixture. It must still ask Sage to construct named classes and project
Sage's actual runtime classes back to provider classes. It must not infer the
category hierarchy from source code.

Completion condition:

- A diamond category fixture produces `ProviderProjection` records where
  `provider_bases` and `provider_mro` exactly equal a direct projection of
  Sage runtime `parent_class.__bases__` and `parent_class.__mro__`.

Validation:

- `just test tests/test_oracle_projection.py -q`
- A failing mutation check performed manually during development: break one
  runtime provider base in the expected manifest and verify the test fails for
  an equality mismatch.

## Manifest Contract

`manifest.py` owns serialization, schema validation, and lookup.

Required manifest fields:

```text
schema_version
generated_by
sage_version
python_version
projections[]
```

Each projection record contains exactly the fields in `ProviderProjection`.
Unknown schema versions, missing required fields, non-string fullnames, and
non-list MRO fields are hard failures. The core does not silently synthesize
missing providers.

Completion condition:

- A known-good fixture manifest round-trips to `ProviderProjection`.
- Malformed manifests fail before the mypy plugin mutates any `TypeInfo`.

Validation:

- `just test tests/test_manifest.py -q`

## Mypy Projection Contract

`plugin.py` owns only the thin projection from manifest data into mypy.

Implemented hooks:

- `plugin(version: str)`
- `get_customize_class_mro_hook(fullname: str)`
- `get_additional_deps(file)`
- `report_config_data(ctx)`

Required behavior:

- If `fullname` has no manifest projection, do nothing.
- If `fullname` has a projection, resolve every `provider_bases` entry to a
  loaded `TypeInfo`.
- Mutate the current `TypeInfo` so mypy sees the manifest provider bases.
- Assert or report that resulting `info.mro` fullnames equal
  `provider_mro`.
- In strict mode, unresolved manifest records, missing provider bases, and MRO
  mismatches are plugin errors.
- In non-strict mode, unresolved projection is still non-teaching behavior and
  must be observable in debug output or test evidence. It must not become a
  fallback that makes a behavioral test pass.

Completion condition:

- A structural plugin test observes the mypy-analyzed `TypeInfo` for a fixture
  provider class and asserts exact equality with the manifest `provider_mro`.

Validation:

- `just test tests/test_plugin_projection.py -q`

## Behavioral Proof Contract

Behavioral tests are downstream proof that standard mypy rules now fire against
the projected MRO. They do not substitute for the structural equality test.

Required first behavior surfaces:

- Valid `@override`: plugin off fails with no-base; plugin on passes.
- Invalid `@override`: plugin off fails with no-base; plugin on fails with
  no-base because no Sage ancestor provides the method.
- `@final` violation: plugin on fails with mypy's standard final-override
  diagnostic.
- Signature mismatch: plugin on fails with mypy's standard incompatible
  override diagnostic.

Completion condition:

- Each behavior is asserted through plugin-on/plugin-off conjunctions.
- Invalid plugin-on cases stay invalid for ordinary mypy reasons.

Validation:

- `just test tests/test_behavior_matrix.py -q`

## Implementation Phases

## Branch Containment

Where:

- `rewrite/invariant-core`
- `/home/dzack/sage-mypy-plugin-rewrite`

What:

- Keep the existing main worktree and stale staged WIP untouched.
- Commit this plan as the first rewrite artifact.
- Before deleting legacy code, create a commit boundary so the plan is
  recoverable independently of later archive/removal commits.

Prerequisites:

- Branch exists and `git status --short` is clean in the rewrite worktree.

Acceptance:

- `.serena/plans/invariant-core-rewrite.md` exists on
  `rewrite/invariant-core`.
- No implementation files have changed in the plan commit.

Validation:

- `git status --short`
- `git diff --name-status HEAD`

## Legacy Removal

Where:

- `sage_mypy_category_plugin/`
- `sage-stubs/`
- `tests/`
- tracked `__pycache__/`
- stale package metadata if present

What:

- Remove the legacy implementation and tests from the rewrite branch.
- Keep docs and guidance files.
- Replace stale package/test commands with minimal skeleton tooling that does
  not claim green behavior before new tests exist.

Prerequisites:

- The plan file is committed.

Acceptance:

- Legacy plugin/stub/test files are absent from the rewrite branch.
- `pyproject.toml` names the package but does not advertise unsupported
  behavior.
- `justfile` contains only commands that apply to the rewrite skeleton.

Validation:

- `git diff --name-status HEAD`
- `git status --short`
- `just --list`

## Oracle First Test

Where:

- `tests/fixtures/invariant_core/diamond_runtime.py`
- `tests/test_oracle_projection.py`
- `sage_mypy_category_plugin/oracle.py`

What:

- Write the diamond category fixture.
- Write the failing projection equality test first.
- Implement the minimum Sage-runtime oracle needed to pass that test.

Prerequisites:

- Legacy code has been removed from the branch.
- Sage Python is available through the project just recipes.

Acceptance:

- The oracle reports provider bases and provider MRO from Sage runtime, not
  source reconstruction.

Validation:

- RED: `just test tests/test_oracle_projection.py -q` fails with missing
  oracle behavior.
- GREEN: the same command passes after implementation.
- Mutation check: corrupt one expected provider fullname and verify failure.

## Manifest Validation

Where:

- `sage_mypy_category_plugin/manifest.py`
- `tests/test_manifest.py`

What:

- Add schema validation and JSON load/save for `ProviderProjection`.
- Ensure malformed input fails before plugin projection.

Prerequisites:

- Oracle data model is stable for the diamond fixture.

Acceptance:

- Good manifest round-trips.
- Bad schema, missing fields, and wrong field types fail deterministically.

Validation:

- RED/GREEN with `just test tests/test_manifest.py -q`

## Thin Plugin Projection

Where:

- `sage_mypy_category_plugin/plugin.py`
- `tests/test_plugin_projection.py`
- `tests/mypy_plugin.ini`

What:

- Load the manifest from config.
- Add only the MRO customization, dependency, and cache-reporting hooks.
- Teach mypy provider MRO from manifest data.
- Add structural introspection in tests to assert mypy `TypeInfo.mro`
  fullnames equal manifest `provider_mro`.

Prerequisites:

- Manifest validation is complete.

Acceptance:

- The plugin cannot make a fixture pass unless its `TypeInfo.mro` matches the
  manifest projection.

Validation:

- RED/GREEN with `just test tests/test_plugin_projection.py -q`

## Behavior Matrix

Where:

- `tests/fixtures/invariant_core/diamond_behavior_*.py`
- `tests/test_behavior_matrix.py`

What:

- Add the first behavior matrix tests after structural projection passes.
- Assert plugin-on/off and valid/invalid outcomes together.

Prerequisites:

- Structural mypy MRO equality test passes.

Acceptance:

- Valid override passes only with plugin on.
- Invalid override, final violation, and signature mismatch fail for ordinary
  mypy reasons with plugin on.

Validation:

- RED/GREEN with `just test tests/test_behavior_matrix.py -q`
- Full current rewrite suite through `just test -q`

## First Category Specs Shape

Where:

- A new fixture under `tests/fixtures/invariant_core/category_specs_like/`
- Potential oracle extensions only

What:

- Add one local-wrapper/package-shaped fixture derived from real
  `category_specs` evidence.
- Start with oracle equality, not output suppression.
- Extend only the oracle if Sage runtime truth is not yet captured.

Prerequisites:

- Diamond structural and behavior tests pass.

Acceptance:

- The package-shaped fixture has a Sage-runtime provider projection and mypy
  structural equality test before any behavioral test is accepted.

Validation:

- `just test tests/test_oracle_projection.py tests/test_plugin_projection.py -q`

## System Validation

System validation runs only after the core phases pass.

Required checks:

- `just test -q`
- `just consumer-mypy` for evidence only

Consumer output must not drive new plugin code directly. Any consumer failure
to address must first become a small oracle-backed structural test.

## Stop Rules

Stop implementation if any proposed change:

- Uses source AST to infer Sage category semantics.
- Filters or deletes mypy diagnostics.
- Adds fallback logic that returns `Any`, `object`, or empty tuples to make a
  behavior test pass.
- Adds a hook outside the approved core hook set.
- Adds a behavior test before the structural MRO equality test for that shape.
- Makes `just consumer-mypy` cleaner without a corresponding oracle equality
  test.
- Requires editing `/home/dzack/research/category_specs` without user signoff.

## Rollback

Rollback boundary:

- The rewrite branch starts at `59ec5e2`.
- The plan commit is the first rewrite artifact.
- Legacy removal must be a separate commit from new core implementation.

Rollback method:

- If the rewrite direction is wrong, abandon `rewrite/invariant-core` without
  touching `main`.
- If a later phase goes wrong, revert the phase commit and keep the plan plus
  earlier green phases.

## Completion Definition

The rewrite core is not complete when tests are merely green. It is complete
when:

- Oracle projection equals Sage runtime provider MRO for at least the diamond
  fixture.
- Manifest validation rejects malformed projection data.
- Mypy `TypeInfo.mro` equals manifest `provider_mro` for the handled provider.
- The first behavior matrix passes and invalid plugin-on examples remain
  invalid for standard mypy reasons.
- The codebase contains no legacy fallback/suppression path in the core.
