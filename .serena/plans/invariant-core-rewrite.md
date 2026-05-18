# Sage Mypy Plugin Final-State Rewrite Plan

> **For agents:** Use subagent delegation for independent lanes. Keep worker write
> scopes disjoint, run RED/GREEN/REFACTOR for every code change, and do not let
> consumer error counts drive implementation.

**Goal:** Build the final correct Sage category mypy plugin: a Sage-runtime
oracle plus a thin mypy projection layer that makes mypy's provider-class MRO
match Sage's runtime named-class MRO for all supported category method
providers.

**Architecture:** Sage computes category semantics in a resolver subprocess.
The resolver emits a validated manifest. The mypy plugin reads only that
manifest and projects provider-class inheritance into mypy's normal TypeInfo
graph so standard mypy rules handle `@override`, `@final`, abstract methods,
properties, overloads, and signature compatibility.

**Tech Stack:** Sage Python, mypy plugin API, Pydantic validation, pytest
through `just`, JSON manifests, GitHub/PR review for large integration stages.

---

## Defect Statement

The previous implementation rewarded local error reduction instead of semantic
truth. It accumulated source discovery, fallback MRO synthesis, constructor
hooks, receiver inference, diagnostic filtering, and stubs. Those mechanisms
can make fixtures or consumers cleaner without proving the plugin taught mypy
the same inheritance Sage actually constructs at runtime.

The rewrite is correct only when this invariant holds for every handled
provider class:

```text
mypy TypeInfo MRO
==
project_provider_classes(Sage runtime named-class __mro__)
```

Behavioral success is downstream. A behavior test that passes without the
structural invariant is not proof.

## Canonical Sources

- `AGENTS.md`: repository contract, banned patterns, local-wrapper fixture
  requirements, and owned test surface.
- `GOALS.md`: known surfaces and historical warnings about suppressions.
- `/home/dzack/vault/projects/sagemath-mypy-plugin/Mypy Plugin for Sage.md`:
  final target architecture and critique of reward-hacking failure modes.
- Sage runtime: sole source of category named classes, bases, MROs, axioms,
  functorial constructions, and concrete category behavior.
- Mypy: sole checker for decorator, override, inheritance, and signature
  semantics after inheritance facts are projected.

## Non-Negotiable Constraints

- No source-AST reconstruction of Sage category semantics in the core.
- No diagnostic filtering in the core.
- No `Any`, `object`, empty-MRO, or synthesized-provider fallback that makes a
  test pass.
- No Sage import from the mypy plugin in default mode.
- No namespace prefix assumptions such as `sage.categories.`.
- No direct-Sage-subclass third-party fixtures.
- No behavior test before a structural equality test for the same shape.
- No plugin-on-only success tests.
- No consumer-driven patching. Consumer failures must first become small
  oracle-backed structural tests.
- No new hooks in the core beyond manifest loading, MRO projection, dependency
  ordering, and cache invalidation.
- No manual bypass of `just` recipes for tests, type checks, builds, or
  consumer validation once a recipe exists.

## Final Correct State

The project is complete when all of these are true:

- The resolver traces Sage named-class construction instead of reconstructing
  category hierarchy from source.
- The manifest records runtime class identity, provider identity, direct bases,
  full runtime MRO, projected provider bases, projected provider MRO, module
  hashes, Sage/Python/mypy/plugin schema versions, and concrete parent records
  where supported.
- The plugin loads the manifest, resolves provider TypeInfos, mutates provider
  bases/MRO, reports cache data, and fails loudly in strict mode on stale or
  unresolved projection data.
- Structural tests prove `TypeInfo.mro == manifest.provider_mro` for every
  supported provider shape before behavior tests are accepted.
- Behavior tests use plugin-on/off and valid/invalid matrices.
- Supported surfaces include local-wrapper namespaces, parent providers,
  element providers, subcategory providers, morphism providers, homsets,
  axioms, linked axiom classes, functorial constructions, parameterized
  categories, concrete parent initialization, narrow generated stubs, self-type
  support where explicitly proved, and Cython boundaries where visible through
  source or stubs.
- `category_specs` is validated as an evidence consumer, not used as the
  implementation oracle.
- CI pins supported mypy versions and fails on manifest/cache invalidation
  regressions.

## Agent Execution Model

Use parallel Spark-style subagents only for work with disjoint write sets.

- Resolver worker owns `oracle.py`, resolver CLI, Sage tracing tests, and Sage
  fixture forcing logic.
- Manifest worker owns `manifest.py`, schema migrations, digest/cache fields,
  and malformed-manifest tests.
- Plugin worker owns `plugin.py`, hook behavior, TypeInfo projection, strict
  errors, and mypy cache reporting.
- Fixture/test worker owns fixture packages, matrix tests, and mutation checks.
- Consumer worker owns read-only `category_specs` evidence collection and
  conversion of observed failures into repo-local fixtures.
- Review worker audits for banned patterns, fallback logic, weak tests, and
  performance regressions.

Workers may run in parallel only when their files do not overlap. Integration
and conflict resolution stay with the lead agent.

## Phase: Stabilize The Rewrite Contract

**Objective:** Make the branch plan and acceptance criteria impossible to
confuse with consumer error cleanup.

**Files:**
- Modify: `.serena/plans/invariant-core-rewrite.md`
- Inspect: `AGENTS.md`, `GOALS.md`, vault project note

**Prerequisites:** Branch is `rewrite/invariant-core`; worktree state is known.

**Acceptance:**
- The plan defines final state, not only the next local task.
- Stop rules forbid the known historical hacks.
- Subagent lanes and write ownership are explicit.

**Validation:**
- `git diff -- .serena/plans/invariant-core-rewrite.md`
- `just --list`

## Phase: Resolver Tracing Becomes The Oracle

**Objective:** Replace explicit-category reconstruction with direct tracing of
Sage named-class construction.

**Files:**
- Modify: `sage_mypy_category_plugin/oracle.py`
- Create or modify: resolver CLI module under `sage_mypy_category_plugin/`
- Test: `tests/test_oracle_projection.py`
- Fixture: `tests/fixtures/invariant_core/`

**Work:**
- Add a failing Sage-side test that proves a traced record comes from
  `Category._make_named_class`.
- Trace `Category._make_named_class` in a Sage subprocess and record returned
  class identity, direct bases, full MRO, method provider, category class, and
  role.
- Add a bounded secondary trace of `sage.structure.dynamic_class.dynamic_class`
  only if a real fixture proves `_make_named_class` is insufficient.
- Force named classes through Sage APIs: `parent_class`, `element_class`,
  `subcategory_class`, `morphism_class`, and homset named classes where
  constructible.
- Project runtime classes back to provider classes using the traced provider,
  not source hierarchy inference.

**Acceptance:**
- Diamond and local-wrapper fixtures produce provider bases and provider MROs
  directly from traced runtime classes.
- Mutation of one runtime/provider mapping fails an equality test.
- No source parser or namespace prefix logic participates in projection.

**Validation:**
- `just test tests/test_oracle_projection.py -q`
- Manual mutation check with restored diff afterward.
- `rg "sage\\.categories|find\\(\"sage|except Exception|Any|object" sage_mypy_category_plugin`
  followed by review of every hit.

## Phase: Manifest Is A Strict Contract

**Objective:** Turn resolver output into a stable, invalidation-aware contract
between Sage and mypy.

**Files:**
- Modify: `sage_mypy_category_plugin/manifest.py`
- Test: `tests/test_manifest.py`
- Fixtures: manifest samples under `tests/fixtures/invariant_core/`

**Work:**
- Extend the manifest schema with schema version, generator version, Sage
  version, Sage git revision when available, Python version, supported mypy
  interval, plugin schema version, module paths, mtimes, content hashes,
  named-class records, provider projections, and concrete parent records.
- Validate fullnames, roles, runtime identities, direct bases, MROs, source
  module hashes, and record uniqueness.
- Reject missing required fields, unknown schema versions, malformed lists,
  duplicate provider records, and unresolved provider references.
- Add digest computation for `report_config_data`.

**Acceptance:**
- A valid traced manifest round-trips without losing provider identity.
- Malformed manifests fail before mypy TypeInfo mutation.
- Manifest digest changes when semantic projection data changes.

**Validation:**
- `just test tests/test_manifest.py -q`
- Focused mutation checks for schema version, duplicate providers, and stale
  digest data.

## Phase: Thin Mypy Projection Core

**Objective:** Keep the plugin limited to manifest projection into mypy's
inheritance graph.

**Files:**
- Modify: `sage_mypy_category_plugin/plugin.py`
- Test: `tests/test_plugin_projection.py`
- Config fixtures: `tests/mypy_plugin*.ini`

**Work:**
- Load manifest config and fail clearly when strict mode cannot proceed.
- Implement only `plugin`, `get_customize_class_mro_hook`,
  `get_additional_deps`, and `report_config_data` in the core.
- Resolve every provider base to a loaded `TypeInfo`.
- Mutate provider bases and MRO so the observed `TypeInfo.mro` equals the
  manifest provider MRO.
- Make projection idempotent across mypy incremental passes.
- Report manifest digest, schema versions, Sage version, and mypy/plugin
  compatibility through cache data.

**Acceptance:**
- A structural plugin test can inspect analyzed TypeInfos and prove exact MRO
  equality.
- Missing providers, stale manifests, and MRO mismatches are strict errors.
- There is no diagnostic filtering or behavior-specific decorator logic.

**Validation:**
- `just test tests/test_plugin_projection.py -q`
- `sage -python -m mypy --config-file=/dev/null ...` through an approved
  `just` recipe once present.

## Phase: Behavioral Proof Matrix

**Objective:** Prove standard mypy rules fire because inheritance is correct.

**Files:**
- Modify: `tests/test_behavior_matrix.py`
- Fixture: `tests/fixtures/invariant_core/*_behavior_*.py`

**Work:**
- For each behavior, write the failing matrix first:
  plugin off valid, plugin on valid, plugin off invalid, plugin on invalid.
- Cover valid `@override`, invalid `@override`, missing explicit override,
  `@final` override, signature mismatch, abstract method implementation,
  property override, classmethod/staticmethod override, overload override.
- Assert exact error codes where mypy exposes them and avoid string-only
  proof except where mypy has no structured alternative.

**Acceptance:**
- Plugin-on valid cases pass only after structural projection works.
- Plugin-on invalid cases still fail for ordinary mypy reasons.
- Plugin-off valid cases fail for the blindness the plugin owns.

**Validation:**
- `just test tests/test_behavior_matrix.py -q`
- `just test -q`

## Phase: Category Specs Shape Before Category Specs Output

**Objective:** Prove the real consumer shape without editing the consumer.

**Files:**
- Create: `tests/fixtures/invariant_core/category_specs_like/`
- Modify: oracle, manifest, and plugin tests only as structurally required

**Work:**
- Build a fixture package that mirrors the consumer's local wrapper base,
  namespace layout, and category/subcategory pattern.
- Start with oracle projection equality and plugin TypeInfo equality.
- Add behavior matrices only after structural equality passes.
- Convert any observed `category_specs` failure into the smallest local fixture
  that reproduces the semantic shape.

**Acceptance:**
- Local-wrapper namespace behavior is proven without direct Sage subclass
  shortcuts.
- The fixture would fail under the historical namespace-prefix bug.

**Validation:**
- `just test tests/test_oracle_projection.py tests/test_plugin_projection.py -q`
- `just test tests/test_behavior_matrix.py -q`

## Phase: Role Coverage

**Objective:** Extend the invariant across Sage's method-provider roles.

**Files:**
- Modify: `oracle.py`, `manifest.py`, `plugin.py`
- Tests: role-specific structural and behavior tests
- Fixtures: parent, element, subcategory, morphism, homset providers

**Work:**
- Add `ParentMethods`, `ElementMethods`, `SubcategoryMethods`,
  `MorphismMethods`, `Homsets.ParentMethods`, and `Homsets.ElementMethods`.
- For each role, add structural Sage projection tests first.
- Add behavior matrices for role-owned override/final/signature surfaces.

**Acceptance:**
- Each supported role has structural equality proof.
- Role behavior tests are not accepted without structural proof.

**Validation:**
- Role-targeted `just test ... -q`
- Full `just test -q`

## Phase: Axioms And Linked Axiom Classes

**Objective:** Support Sage's `with_axiom` machinery by evaluating Sage, not by
hardcoding axiom names.

**Files:**
- Modify: resolver/oracle forcing logic
- Fixtures: axiom and linked-axiom packages
- Tests: oracle, plugin, behavior matrices

**Work:**
- Force representative axiom categories such as finite variants through Sage.
- Add a linked axiom class fixture using lazy import shape when feasible.
- Record the named classes Sage actually constructs and their provider MROs.

**Acceptance:**
- Axiom categories project provider MRO from Sage runtime.
- Linked axiom classes do not require namespace or filename heuristics.

**Validation:**
- Targeted oracle and plugin tests for axiom fixtures.
- Behavior matrix for at least one axiom override surface.

## Phase: Functorial Constructions

**Objective:** Delegate construction-category semantics to Sage.

**Files:**
- Modify: resolver/oracle construction forcing
- Fixtures: Cartesian products, tensor products, and one consumer-shaped
  construction if observed
- Tests: structural and behavior matrices

**Work:**
- Use Sage construction APIs such as category-from-category/categories/parents
  rather than encoding construction rules.
- Force named classes on the returned category objects.
- Record provider projections and cache dependencies.

**Acceptance:**
- Functorial provider MROs match Sage runtime under structural tests.
- No construction-specific mypy heuristic is added.

**Validation:**
- Targeted functorial fixture tests.
- Full suite through `just`.

## Phase: Parameterized Categories

**Objective:** Handle categories whose class sharing depends on Sage runtime
identity rather than raw constructor arguments.

**Files:**
- Modify: resolver record identity/fingerprint logic
- Modify: manifest uniqueness validation
- Tests: parameter-sharing and parameter-separation fixtures

**Work:**
- Key named-class records by runtime dynamic-class identity and provider-MRO
  fingerprint.
- Prove categories that share runtime named classes share projection records.
- Prove categories with different runtime MROs produce distinct records.

**Acceptance:**
- No raw-argument cache key determines semantic identity.
- Sharing/separation tests fail under naive constructor-argument handling.

**Validation:**
- `just test tests/test_oracle_projection.py tests/test_manifest.py -q`

## Phase: Concrete Parents And Elements

**Objective:** Support concrete classes initialized into Sage categories without
claiming unknown dynamic category choices are known.

**Files:**
- Modify: resolver concrete parent record generation
- Modify: manifest concrete parent schema
- Optional plugin extension only after structural tests prove need
- Fixtures: `Parent.__init__(category=...)`, `_init_category_(...)`, nested
  element classes

**Work:**
- Record concrete parent category initialization when statically forced by
  Sage runtime execution.
- Record runtime dynamic class and category provider base.
- Add structural tests before deciding whether to inject provider bases into
  concrete classes or expose generated aliases.

**Acceptance:**
- Known category initialization is represented from Sage runtime evidence.
- Unknown runtime-selected categories remain unknown and do not get synthetic
  precision.

**Validation:**
- Concrete-parent structural tests.
- Behavior matrices only for owned static surfaces.

## Phase: Generated Stubs And Self Types

**Objective:** Add annotation support without making stubs the source of
category truth.

**Files:**
- Create: generated stub module path under project-controlled output
- Modify: manifest-to-stub generator
- Tests: generated-stub contract tests and mypy behavior tests

**Work:**
- Generate aliases/protocols from manifest records only.
- Add parent/element aliases for annotation use.
- Add provider self-type support through generated protocols or stable mypy
  hooks only after tests prove the exact owned contract.

**Acceptance:**
- Generated stubs are reproducible from the manifest.
- Stub changes cannot hide a wrong provider MRO.
- Self-type behavior has plugin-on/off proof and invalid-case proof.

**Validation:**
- Stub generation diff check.
- Mypy behavior tests through `just`.

## Phase: Cython And External Boundaries

**Objective:** Be precise where mypy can see source/stubs and conservative
where it cannot.

**Files:**
- Modify: resolver classification of runtime classes
- Modify: manifest external-class metadata
- Tests: Cython-backed source/stub/no-stub fixtures where available

**Work:**
- Distinguish Python provider methods, Cython classes with `.pyi`, and Cython
  classes without static signatures.
- Use visible stubs where available.
- Refuse precise override claims where mypy cannot see signatures.

**Acceptance:**
- The plugin does not invent signatures for invisible Cython surfaces.
- Conservative boundaries are explicit in manifest metadata and tests.

**Validation:**
- Targeted external-boundary tests.
- Full suite.

## Phase: Consumer Validation

**Objective:** Use `category_specs` as evidence after local invariants cover its
shapes.

**Files:**
- Modify only repo-local fixtures and plugin code.
- Do not edit `/home/dzack/research/category_specs` without explicit signoff.

**Work:**
- Run the consumer through a `just consumer-mypy` recipe.
- Classify each failure by missing structural shape, missing behavior matrix,
  external dependency/stub gap, or true consumer error.
- For plugin-owned gaps, add the smallest repo-local structural fixture first.
- Re-run consumer only after local tests prove the shape.

**Acceptance:**
- Consumer improvements are explained by local structural tests.
- Remaining consumer failures are classified with evidence, not patched around.

**Validation:**
- `just consumer-mypy`
- Local fixture test proving each fixed shape.

## Phase: CI, Performance, And Release Discipline

**Objective:** Make correctness reproducible for future agents and mypy/Sage
updates.

**Files:**
- Modify: `justfile`, `pyproject.toml`, CI config if present
- Tests: cache invalidation and supported-version matrix

**Work:**
- Pin supported mypy minor versions or an explicit tested interval.
- Add recipes for resolver generation, structural tests, behavior tests,
  mutation checks, consumer evidence, type checking, and release checks.
- Keep tests focused on real invariants and remove slow or duplicate checks.
- Include manifest digest and dependency data in cache invalidation tests.

**Acceptance:**
- A clean checkout can run the full supported validation path through `just`.
- Test runtime regressions are treated as failures to investigate, not accepted
  as normal for this plugin.
- Release artifacts declare supported Sage/mypy/plugin schema versions.

**Validation:**
- `just --list`
- `just test -q`
- supported mypy matrix recipe
- consumer evidence recipe

## Cross-Cutting Test Rules

- Every production change starts with a failing test.
- Every behavior surface is a conjunction matrix.
- Every structural surface asserts Sage runtime projection and mypy TypeInfo
  equality.
- Tests must use real Sage runtime objects and real mypy runs.
- No mocks, simulations, `xfail`, skip-based masking, or content-free checks.
- Mutation checks are required for projection code that could otherwise pass
  with arbitrary nonempty output.

## Stop Rules

Stop work and report if a proposed change requires:

- Reintroducing source-based category semantic inference in the core.
- Filtering mypy diagnostics.
- Making a consumer error disappear without a local structural test.
- Adding broad stubs that claim unproved Sage behavior.
- Editing `category_specs` without signoff.
- Proceeding when Sage, mypy, or `just` commands needed for the phase are not
  available.
- Accepting a test that passes before the intended implementation exists.
- Adding fallback logic to paper over missing provider data.

## Rollback

The rewrite branch is the containment boundary. Each phase must land in its own
commit once accepted. If a phase breaks the invariant, revert that phase commit
and keep earlier green phases. If the final-state architecture is rejected,
abandon `rewrite/invariant-core`; do not mutate `main` to recover.
