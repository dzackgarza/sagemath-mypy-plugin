from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from importlib import import_module
from pathlib import Path

from mypy.build import BuildResult, build
from mypy.modulefinder import BuildSource
from mypy.options import Options

from sage_mypy_category_plugin.manifest import (
    ProjectionManifest,
    SourceModuleRecord,
    load_manifest,
    write_manifest,
)
from sage_mypy_category_plugin.oracle import provider_projections_for_categories
from sage_mypy_category_plugin.projection import ProviderProjection
from tests.manifest_helpers import external_runtime_class_records_for_test_manifest

type SourceTree = dict[str, "SourceTree"]

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "invariant_core"
REAL_CATEGORIES_ROOT = REPO_ROOT / "tests" / "real_categories"
E5_ROOT = REPO_ROOT / "tests" / "fixtures" / "e5_renamed_consumer"
FINITE_SMALL_GROUPS_VALID = "tests.real_categories.finite_small_groups_valid"
FINITE_SMALL_GROUPS_INVALID = "tests.real_categories.finite_small_groups_invalid"
FINITE_SMALL_GROUPS_SIGNATURE_MISMATCH = (
    "tests.real_categories.finite_small_groups_signature_mismatch"
)
FINITE_SMALL_GROUPS_MISSING_EXPLICIT_OVERRIDE = (
    "tests.real_categories.finite_small_groups_missing_explicit_override"
)
FINITE_POSETS_MODULE = "tests.real_categories.finite_posets"
E5_VALID_MODULE = "tests.fixtures.e5_renamed_consumer.valid_override"
E5_INVALID_MODULE = "tests.fixtures.e5_renamed_consumer.invalid_override"
BASE_CATEGORY_FULLNAMES = (
    "tests.fixtures.invariant_core.diamond_runtime.TopCategory",
    "tests.fixtures.invariant_core.diamond_runtime.LeftCategory",
    "tests.fixtures.invariant_core.diamond_runtime.RightCategory",
    "tests.fixtures.invariant_core.diamond_runtime.BottomCategory",
)
COMMUTATIVE_RINGS_CATEGORY = "sage.categories.commutative_rings.CommutativeRings"
COMMUTATIVE_RINGS_PROVIDER = (
    "sage.categories.commutative_rings.CommutativeRings.ParentMethods"
)
RINGS_PROVIDER = "sage.categories.rings.Rings.ParentMethods"
FUNCTORIAL_CARTESIAN_CATEGORY = (
    "tests.fixtures.invariant_core.functorial.cartesian_products."
    "CartesianProductsCategory"
)
SETS_PROVIDER = "sage.categories.sets_cat.Sets.ParentMethods"
FUNCTORIAL_CARTESIAN_PARENT_PROVIDER = (
    "sage.categories.sets_cat.Sets.CartesianProducts.ParentMethods"
)
PARAMETERIZED_CATEGORY_FULLNAMES = (
    "tests.fixtures.invariant_core.parameterized.ModulesOverIntegers",
    "tests.fixtures.invariant_core.parameterized.ModulesOverRationals",
    "tests.fixtures.invariant_core.parameterized.VectorSpacesOverRationals",
)
MODULES_PROVIDER = "sage.categories.modules.Modules.ParentMethods"
VECTOR_SPACES_PROVIDER = "sage.categories.vector_spaces.VectorSpaces.ParentMethods"
AXIOM_ROOT_CATEGORY = "tests.fixtures.invariant_core.axioms.AxiomRootCategory.Finite"
AXIOM_BEHAVIOR_CASES = {
    "axiom_valid": (
        "tests.fixtures.invariant_core.axiom_behavior_valid",
        "tests.fixtures.invariant_core.axiom_behavior_valid.ValidAxiomOverrideCategory.Finite",
    ),
    "axiom_invalid": (
        "tests.fixtures.invariant_core.axiom_behavior_invalid",
        "tests.fixtures.invariant_core.axiom_behavior_invalid.InvalidAxiomOverrideCategory.Finite",
    ),
}
BEHAVIOR_CASES = {
    "valid": (
        "tests.fixtures.invariant_core.diamond_behavior_valid",
        "tests.fixtures.invariant_core.diamond_behavior_valid.ValidOverrideCategory",
    ),
    "invalid": (
        "tests.fixtures.invariant_core.diamond_behavior_invalid",
        "tests.fixtures.invariant_core.diamond_behavior_invalid.InvalidOverrideCategory",
    ),
    "final": (
        "tests.fixtures.invariant_core.diamond_behavior_final_violation",
        "tests.fixtures.invariant_core.diamond_behavior_final_violation.FinalBaseCategory",
        "tests.fixtures.invariant_core.diamond_behavior_final_violation.FinalViolationCategory",
    ),
    "signature": (
        "tests.fixtures.invariant_core.diamond_behavior_signature_mismatch",
        "tests.fixtures.invariant_core.diamond_behavior_signature_mismatch.SignatureBaseCategory",
        "tests.fixtures.invariant_core.diamond_behavior_signature_mismatch.SignatureMismatchCategory",
    ),
    "missing_explicit_override": (
        "tests.fixtures.invariant_core.diamond_behavior_missing_explicit_override",
        "tests.fixtures.invariant_core.diamond_behavior_missing_explicit_override.MissingExplicitOverrideCategory",
    ),
    "decorated_valid": (
        "tests.fixtures.invariant_core.diamond_behavior_decorated_valid",
        "tests.fixtures.invariant_core.diamond_behavior_decorated_base.DecoratedBaseCategory",
        "tests.fixtures.invariant_core.diamond_behavior_decorated_valid.ValidDecoratedOverrideCategory",
    ),
    "decorated_invalid": (
        "tests.fixtures.invariant_core.diamond_behavior_decorated_invalid",
        "tests.fixtures.invariant_core.diamond_behavior_decorated_base.DecoratedBaseCategory",
        "tests.fixtures.invariant_core.diamond_behavior_decorated_invalid.InvalidDecoratedOverrideCategory",
    ),
}


def test_behavior_matrix_uses_standard_mypy_inheritance_rules(tmp_path: Path) -> None:
    config_path = _write_plugin_config(tmp_path)

    with_plugin = _run_mypy(
        tuple(case[0] for case in BEHAVIOR_CASES.values()),
        config_path,
        tmp_path,
    )
    without_plugin = _run_mypy_without_plugin(
        tuple(case[0] for case in BEHAVIOR_CASES.values()),
        tmp_path,
    )

    assert not _case_errors(with_plugin, "valid")
    assert _case_contains(without_plugin, "valid", "no base method was found")
    assert _case_contains(with_plugin, "invalid", "no base method was found")
    assert _case_contains(without_plugin, "invalid", "no base method was found")
    assert _case_contains(with_plugin, "final", "Cannot override final attribute")
    assert _case_contains(without_plugin, "final", "no base method was found")
    assert _case_contains(with_plugin, "signature", 'Argument 1 of "signature_method"')
    assert _case_contains(with_plugin, "signature", "[override]")
    assert _case_contains(without_plugin, "signature", "no base method was found")
    assert _case_contains(with_plugin, "missing_explicit_override", "[explicit-override]")
    assert not _case_errors(without_plugin, "missing_explicit_override")
    assert not _case_errors(with_plugin, "decorated_valid")
    assert _case_contains(without_plugin, "decorated_valid", "no base method was found")
    assert _case_contains_fragments(
        with_plugin,
        "decorated_invalid",
        "decorated_property",
        "[override]",
    )
    assert _case_contains_fragments(
        with_plugin,
        "decorated_invalid",
        "decorated_classmethod",
        "[override]",
    )
    assert _case_contains_fragments(
        with_plugin,
        "decorated_invalid",
        "decorated_staticmethod",
        "[override]",
    )
    assert _case_contains_fragments(
        with_plugin,
        "decorated_invalid",
        "decorated_abstract",
        "[override]",
    )
    assert _case_contains_fragments(
        with_plugin,
        "decorated_invalid",
        "decorated_overload",
        "[override]",
    )
    assert _case_contains(
        without_plugin,
        "decorated_invalid",
        "no base method was found",
    )


def test_nested_sage_provider_behavior_matrix_uses_standard_mypy_rules(
    tmp_path: Path,
) -> None:
    with_plugin = _run_nested_provider_mypy(tmp_path, with_plugin=True)
    without_plugin = _run_nested_provider_mypy(tmp_path, with_plugin=False)

    assert not _contains_error(with_plugin, '"is_commutative"')
    assert not _contains_error(with_plugin, '"construction"')
    assert not _contains_error(with_plugin, '"tensor_square"')
    assert _contains_error_fragments(
        with_plugin,
        '"not_a_sage_axiom_method"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        with_plugin,
        '"not_a_sage_functorial_method"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        with_plugin,
        '"not_a_sage_parameterized_method"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        without_plugin,
        '"is_commutative"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        without_plugin,
        '"construction"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        without_plugin,
        '"tensor_square"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        without_plugin,
        '"not_a_sage_axiom_method"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        without_plugin,
        '"not_a_sage_functorial_method"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        without_plugin,
        '"not_a_sage_parameterized_method"',
        "no base method was found",
    )


def test_local_axiom_behavior_matrix_uses_standard_mypy_rules(
    tmp_path: Path,
) -> None:
    visible_sage_stubs = _write_visible_sage_axiom_stubs(tmp_path)
    config_path = _write_axiom_plugin_config(
        tmp_path,
        visible_sage_stubs=visible_sage_stubs,
    )
    modules = tuple(case[0] for case in AXIOM_BEHAVIOR_CASES.values())

    with_plugin = _run_mypy(
        modules,
        config_path,
        tmp_path,
        mypy_path_entries=(REPO_ROOT, visible_sage_stubs),
    )
    without_plugin = _run_mypy_without_plugin(
        modules,
        tmp_path,
        mypy_path_entries=(REPO_ROOT, visible_sage_stubs),
    )

    assert not _case_errors(with_plugin, "axiom_valid")
    assert _case_contains(without_plugin, "axiom_valid", "no base method was found")
    assert _case_contains(with_plugin, "axiom_invalid", "no base method was found")
    assert _case_contains(without_plugin, "axiom_invalid", "no base method was found")


def test_packages_config_behavior_matrix_end_to_end(tmp_path: Path) -> None:
    """Phase 7 E4: packages= config triggers plugin-owned generation; 4-cell conjunction holds.

    This proves the production path (no pre-generated manifest, no external
    MYPYPATH) produces the same behavioral invariant as the debug manifest= path:

      plugin off + valid code   → "no base method was found" (Sage provider invisible)
      plugin on  + valid code   → no errors (plugin projects provider MRO)
      plugin off + invalid code → "no base method was found"
      plugin on  + invalid code → "no base method was found" (mypy still enforces @override)

    The manifest is generated by the plugin during the mypy build
    (plugin.__init__) with no external wrapper or MYPYPATH needed.
    """
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    # In production, users configure the packages containing their Sage category
    # definitions.  ValidOverrideCategory / InvalidOverrideCategory ARE Sage
    # categories (they subclass BottomCategory, which is a real Sage Category),
    # so they must be included in the packages scan — exactly as they would be
    # in a real consumer category_specs package.
    valid_module = BEHAVIOR_CASES["valid"][0]
    invalid_module = BEHAVIOR_CASES["invalid"][0]
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                "packages =",
                "    tests.fixtures.invariant_core.diamond_runtime",
                f"    {valid_module}",
                f"    {invalid_module}",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )

    modules = (BEHAVIOR_CASES["valid"][0], BEHAVIOR_CASES["invalid"][0])

    with_plugin = _run_mypy(modules, config_path, tmp_path)
    without_plugin = _run_mypy_without_plugin(modules, tmp_path)

    # Manifest was auto-generated by the plugin during the mypy build
    assert (cache_dir / "projection-manifest.json").is_file()
    assert not (cache_dir / "stubs").exists()

    # 4-cell behavioral conjunction: provider MROs projected ↔ mypy sees inherited methods
    assert not _case_errors(with_plugin, "valid"), (
        f"Expected no errors for valid code with plugin; got: {_case_errors(with_plugin, 'valid')}"
    )
    assert _case_contains(without_plugin, "valid", "no base method was found"), (
        "Expected valid code to fail without plugin (Sage provider MRO invisible)"
    )
    assert _case_contains(with_plugin, "invalid", "no base method was found"), (
        "Expected invalid @override to still fail with plugin on"
    )
    assert _case_contains(without_plugin, "invalid", "no base method was found")


def test_real_sage_category_behavior_matrix_uses_standard_mypy_rules(
    tmp_path: Path,
) -> None:
    """Phase 3 P3 + Phase 4: real Sage categories satisfy the full behavioral conjunction.

    Uses real Sage categories (FiniteGroupsOfOrderLessThanTwenty subclassing
    Groups().Finite()) — not synthetic LocalCategoryBase fixtures.  This proves
    the plugin correctly projects real Sage runtime provider MROs, not just the
    synthetic diamond graph, and that all standard mypy inheritance rules fire
    correctly when the provider MRO is visible.

    Upstream Sage provider visibility comes from the installed Sage-version
    sidecar stubs; package-mode plugin execution must not generate or expose
    cache_dir/stubs.

    6-cell behavioral conjunction:
      plugin off + valid code                   → "no base method was found"
      plugin on  + valid code                   → no errors
      plugin off + invalid code (@override DNE) → "no base method was found"
      plugin on  + invalid code                 → "no base method was found"
      plugin on  + @final violation             → "Cannot override final attribute"
      plugin off + @final violation             → no errors (parent invisible)
      plugin on  + signature mismatch           → [override] signature error
      plugin off + signature mismatch           → "no base method was found"
      plugin on  + missing @override decorator  → [explicit-override]
      plugin off + missing @override decorator  → no errors (parent invisible)
    """
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.real_categories",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )

    valid_path = REAL_CATEGORIES_ROOT / "finite_small_groups_valid.py"
    invalid_path = REAL_CATEGORIES_ROOT / "finite_small_groups_invalid.py"
    final_path = REAL_CATEGORIES_ROOT / "finite_small_groups_final_violation.py"
    sig_mismatch_path = REAL_CATEGORIES_ROOT / "finite_small_groups_signature_mismatch.py"
    missing_override_path = (
        REAL_CATEGORIES_ROOT / "finite_small_groups_missing_explicit_override.py"
    )
    sources = (
        BuildSource(str(valid_path), FINITE_SMALL_GROUPS_VALID, None),
        BuildSource(str(invalid_path), FINITE_SMALL_GROUPS_INVALID, None),
        BuildSource(
            str(final_path),
            "tests.real_categories.finite_small_groups_final_violation",
            None,
        ),
        BuildSource(str(sig_mismatch_path), FINITE_SMALL_GROUPS_SIGNATURE_MISMATCH, None),
        BuildSource(
            str(missing_override_path),
            FINITE_SMALL_GROUPS_MISSING_EXPLICIT_OVERRIDE,
            None,
        ),
    )

    with_plugin = _run_mypy_with_sources(
        sources,
        config_path,
        tmp_path,
        mypy_path_entries=(REPO_ROOT,),
    )
    without_plugin = _run_mypy_without_plugin_with_sources(
        sources,
        tmp_path,
    )
    assert (cache_dir / "projection-manifest.json").is_file()
    assert not (cache_dir / "stubs").exists()

    valid_fn = valid_path.name           # "finite_small_groups_valid.py"
    invalid_fn = invalid_path.name       # "finite_small_groups_invalid.py"
    final_fn = final_path.name           # "finite_small_groups_final_violation.py"
    sig_fn = sig_mismatch_path.name      # "finite_small_groups_signature_mismatch.py"
    missing_fn = missing_override_path.name  # "finite_small_groups_missing_explicit_override.py"

    valid_errors = tuple(e for e in with_plugin.errors if valid_fn in e)
    invalid_errors_on = tuple(e for e in with_plugin.errors if invalid_fn in e)
    valid_errors_off = tuple(e for e in without_plugin.errors if valid_fn in e)
    invalid_errors_off = tuple(e for e in without_plugin.errors if invalid_fn in e)
    final_errors_on = tuple(e for e in with_plugin.errors if final_fn in e)
    final_errors_off = tuple(e for e in without_plugin.errors if final_fn in e)
    sig_errors_on = tuple(e for e in with_plugin.errors if sig_fn in e)
    sig_errors_off = tuple(e for e in without_plugin.errors if sig_fn in e)
    missing_errors_on = tuple(e for e in with_plugin.errors if missing_fn in e)
    missing_errors_off = tuple(e for e in without_plugin.errors if missing_fn in e)

    # Plugin on + valid: no errors (provider MRO projected, @override resolves)
    assert not valid_errors, (
        f"Expected no errors for valid code with plugin; got: {valid_errors}"
    )
    # Plugin off + valid: mypy cannot see real Sage provider class as base
    assert any("no base method was found" in e for e in valid_errors_off), (
        "Expected valid code to fail without plugin (real Sage provider MRO invisible)"
    )

    # Plugin on + invalid (nonexistent method @override): still fails
    assert any("no base method was found" in e for e in invalid_errors_on), (
        "Expected invalid @override to still fail with plugin on"
    )
    assert any("no base method was found" in e for e in invalid_errors_off)

    # Plugin on + @final violation: mypy catches the final override because it
    # sees KleinFourGroups.ParentMethods as the actual base via MRO projection
    assert any("Cannot override final attribute" in e for e in final_errors_on), (
        f"Expected @final violation with plugin on; got: {final_errors_on}"
    )
    # Plugin off + @final violation: no errors at all because mypy cannot see
    # KleinFourGroups.ParentMethods as a base — the method is just a new definition
    assert not final_errors_off, (
        f"Expected no errors without plugin (parent MRO invisible); got: {final_errors_off}"
    )

    # Phase 4: Plugin on + signature mismatch: mypy enforces return-type compatibility
    # has_even_order() -> str is not a subtype of bool → [override]
    assert any("[override]" in e for e in sig_errors_on), (
        f"Expected [override] signature error with plugin on; got: {sig_errors_on}"
    )
    # Plugin off + signature mismatch: parent invisible → "no base method was found"
    assert any("no base method was found" in e for e in sig_errors_off), (
        "Expected signature mismatch to fail differently without plugin "
        f"(no base method); got: {sig_errors_off}"
    )

    # Phase 4: Plugin on + missing @override decorator: [explicit-override] triggered
    # order() overrides parent method but has no @override → explicit-override error
    assert any("[explicit-override]" in e for e in missing_errors_on), (
        f"Expected [explicit-override] with plugin on; got: {missing_errors_on}"
    )
    # Plugin off + missing @override: parent invisible → no error (looks like new method)
    assert not missing_errors_off, (
        f"Expected no errors without plugin (parent invisible); got: {missing_errors_off}"
    )


def test_real_sage_category_identical_method_names_are_projected_independently(
    tmp_path: Path,
) -> None:
    """Phase 3 P5: plugin uses MRO-based projection, not method-name matching.

    finite_small_groups.FiniteGroupsOfOrderLessThanTwenty.ParentMethods defines
    order() and has_even_order().  finite_posets.FinitePosets.ParentMethods
    defines the same method names with different mathematical semantics
    (poset size vs group order).  The two chains are completely unrelated in the
    Sage runtime category graph.

    This test proves that both chains work correctly and independently:
      SmallFinitePosets.ParentMethods.@override order()      → no errors
      SmallFinitePosets.ParentMethods.@override has_even_order() → no errors
      GroupsOfOrderFour.ParentMethods.@override order()      → no errors (same name, different chain)

    If the plugin matched methods by name across chains, one of these would fail.
    """
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.real_categories",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )

    posets_path = REAL_CATEGORIES_ROOT / "finite_posets.py"
    sources = (
        # Include both groups and posets so both are in the same mypy build
        BuildSource(str(REAL_CATEGORIES_ROOT / "finite_small_groups.py"),
                    "tests.real_categories.finite_small_groups", None),
        BuildSource(str(posets_path), FINITE_POSETS_MODULE, None),
    )

    result = _run_mypy_with_sources(
        sources,
        config_path,
        tmp_path,
        mypy_path_entries=(REPO_ROOT,),
    )
    assert (cache_dir / "projection-manifest.json").is_file()
    assert not (cache_dir / "stubs").exists()

    posets_errors = tuple(e for e in result.errors if "finite_posets" in e)
    groups_errors = tuple(e for e in result.errors if "finite_small_groups.py" in e)

    # SmallFinitePosets.order() and has_even_order() override correctly (posets chain)
    assert not posets_errors, (
        f"Expected no errors for finite_posets with plugin; got: {posets_errors}"
    )
    # GroupsOfOrderFour.order() still overrides correctly (groups chain)
    assert not groups_errors, (
        f"Expected no errors for finite_small_groups with plugin; got: {groups_errors}"
    )


def test_cached_run_reuses_manifest_without_regenerating(tmp_path: Path) -> None:
    """Phase 7 E2: second plugin run with valid cache reuses manifest without regenerating.

    Proves cache reuse: _generate_and_cache returns early (no disk write) when
    all source module sha256/mtime records are still fresh.  The manifest file
    content is identical after the second run.

      run 1: cold cache → manifest generated, written to disk
      run 2: warm cache → manifest reused, NOT rewritten to disk
      invariant: sha256(manifest_path) is unchanged after run 2
    """
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    valid_module = BEHAVIOR_CASES["valid"][0]
    invalid_module = BEHAVIOR_CASES["invalid"][0]
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                "packages =",
                "    tests.fixtures.invariant_core.diamond_runtime",
                f"    {valid_module}",
                f"    {invalid_module}",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )

    modules = (valid_module, invalid_module)
    manifest_path = cache_dir / "projection-manifest.json"

    # First run: cold cache — plugin generates and writes manifest
    _run_mypy(modules, config_path, tmp_path)
    assert manifest_path.is_file(), "manifest not generated on first (cold) run"
    digest_after_run1 = sha256(manifest_path.read_bytes()).hexdigest()

    # Second run: warm cache — plugin reuses manifest without rewriting
    _run_mypy(modules, config_path, tmp_path)
    digest_after_run2 = sha256(manifest_path.read_bytes()).hexdigest()

    # Manifest file content is unchanged: cache was reused, not regenerated
    assert digest_after_run2 == digest_after_run1, (
        "manifest was rewritten on second run even though source modules are unchanged; "
        "cache reuse logic did not fire"
    )


def test_stale_source_module_triggers_cache_regeneration(tmp_path: Path) -> None:
    """Phase 7 E3: stale source module metadata forces cache regeneration.

    After generating the manifest, corrupting a source module's sha256 (simulating
    a source mutation that changed the file's content) causes the plugin to discard
    the cached manifest and regenerate it on the next run.

    This proves _source_modules_stale_reason correctly detects metadata mismatches,
    that _try_load_cached_manifest returns None on a stale manifest, and that full
    re-generation records fresh sha256 values — exactly as would happen if the
    developer edited a category source file.

      run 1: cold cache → manifest generated with correct source sha256 values
      corrupt: write wrong sha256 for one local source module record
      run 2: stale manifest detected → discarded → manifest fully regenerated
      invariant: regenerated manifest has the CORRECT sha256 for that source module
    """
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    valid_module = BEHAVIOR_CASES["valid"][0]
    invalid_module = BEHAVIOR_CASES["invalid"][0]
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                "packages =",
                "    tests.fixtures.invariant_core.diamond_runtime",
                f"    {valid_module}",
                f"    {invalid_module}",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )

    modules = (valid_module, invalid_module)
    manifest_path = cache_dir / "projection-manifest.json"

    # First run: cold cache → generates manifest with correct source module metadata
    _run_mypy(modules, config_path, tmp_path)
    assert manifest_path.is_file(), "manifest not generated on first (cold) run"

    # Load the manifest and find a local test-fixture source module to corrupt
    original_manifest = load_manifest(manifest_path)
    local_record = next(
        record for record in original_manifest.source_modules if "tests" in record.module
    )
    actual_sha256 = sha256(Path(local_record.path).read_bytes()).hexdigest()
    assert local_record.sha256 == actual_sha256, (
        "pre-condition: manifest sha256 should match actual file on first run"
    )

    # Corrupt that record's sha256 — simulates the source file having been edited
    wrong_sha256 = "deadbeef" * 8
    assert wrong_sha256 != actual_sha256, "chosen corruption value must differ from actual"
    corrupted_records = tuple(
        record.model_copy(update={"sha256": wrong_sha256})
        if record.module == local_record.module
        else record
        for record in original_manifest.source_modules
    )
    corrupted_manifest = original_manifest.model_copy(
        update={"source_modules": corrupted_records}
    )
    write_manifest(manifest_path, corrupted_manifest)
    corrupted_digest = sha256(manifest_path.read_bytes()).hexdigest()

    # Second run: plugin detects sha256 mismatch → discards corrupted manifest → regenerates
    _run_mypy(modules, config_path, tmp_path)

    regenerated_digest = sha256(manifest_path.read_bytes()).hexdigest()

    # The corrupted manifest was replaced: digest no longer matches the corrupted file
    assert regenerated_digest != corrupted_digest, (
        "plugin did not regenerate manifest after source module sha256 mismatch; "
        "corrupted manifest was silently accepted"
    )

    # The regenerated manifest records the CORRECT sha256 for the source module
    regenerated_manifest = load_manifest(manifest_path)
    regenerated_record = next(
        r for r in regenerated_manifest.source_modules
        if r.module == local_record.module
    )
    regenerated_sha256 = sha256(Path(regenerated_record.path).read_bytes()).hexdigest()
    assert regenerated_record.sha256 == regenerated_sha256, (
        f"regenerated manifest has wrong sha256 for {local_record.module}: "
        f"expected {regenerated_sha256!r}, got {regenerated_record.sha256!r}"
    )


def test_renamed_consumer_package_behavioral_invariant_holds(tmp_path: Path) -> None:
    """Phase 7 E5: plugin works with any consumer package name — no namespace hardcoding.

    tests.fixtures.e5_renamed_consumer is a self-contained Sage category package
    with a completely different namespace from 'category_specs', 'tests.real_categories',
    and 'tests.fixtures.invariant_core'.  The plugin is configured with

        packages = tests.fixtures.e5_renamed_consumer

    and the 4-cell behavioral conjunction must hold on that package's categories,
    proving the plugin reads only from the config-specified packages and contains
    no hardcoded consumer or namespace names.

      plugin off + valid code   → "no base method was found" (Sage provider invisible)
      plugin on  + valid code   → no errors (plugin projects runtime provider MRO)
      plugin off + invalid code → "no base method was found"
      plugin on  + invalid code → "no base method was found" (genuine nonexistent method)
    """
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.e5_renamed_consumer",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )

    valid_path = E5_ROOT / "valid_override.py"
    invalid_path = E5_ROOT / "invalid_override.py"
    sources = (
        BuildSource(str(valid_path), E5_VALID_MODULE, None),
        BuildSource(str(invalid_path), E5_INVALID_MODULE, None),
    )

    with_plugin = _run_mypy_with_sources(
        sources,
        config_path,
        tmp_path,
        mypy_path_entries=(REPO_ROOT,),
    )
    without_plugin = _run_mypy_without_plugin_with_sources(sources, tmp_path)
    assert (cache_dir / "projection-manifest.json").is_file()
    assert not (cache_dir / "stubs").exists()

    # Use full relative paths to avoid substring collisions:
    # "valid_override.py" is a substring of "invalid_override.py".
    valid_rel = str(valid_path.relative_to(REPO_ROOT))    # "tests/fixtures/e5_renamed_consumer/valid_override.py"
    invalid_rel = str(invalid_path.relative_to(REPO_ROOT))  # "tests/fixtures/e5_renamed_consumer/invalid_override.py"
    valid_errors = tuple(e for e in with_plugin.errors if valid_rel in e)
    invalid_errors_on = tuple(e for e in with_plugin.errors if invalid_rel in e)
    valid_errors_off = tuple(e for e in without_plugin.errors if valid_rel in e)
    invalid_errors_off = tuple(e for e in without_plugin.errors if invalid_rel in e)

    # Plugin on + valid: provider MRO projected → @override resolves → no errors
    assert not valid_errors, (
        f"Expected no errors for renamed-consumer valid code with plugin; "
        f"got: {valid_errors}"
    )
    # Plugin off + valid: Sage provider invisible → @override finds no base method
    assert any("no base method was found" in e for e in valid_errors_off), (
        "Expected renamed-consumer valid code to fail without plugin "
        "(Sage provider MRO invisible to plain mypy)"
    )
    # Plugin on + invalid (nonexistent method): still fails with standard mypy rule
    assert any("no base method was found" in e for e in invalid_errors_on), (
        "Expected renamed-consumer invalid @override to still fail with plugin on"
    )
    # Plugin off + invalid: also fails (same error, different root cause)
    assert any("no base method was found" in e for e in invalid_errors_off)


# ── Phase 8: Mutation tests ─────────────────────────────────────────────────


def _ghost_provider_projection(ghost_provider: str) -> ProviderProjection:
    """A schema-valid projection for a provider class that does not exist in Python.

    The manifest schema requires closed-world consistency: every provider name
    referenced in provider_bases or provider_mro must appear as a declared projection.
    This helper creates such a declaration while leaving the class genuinely absent
    from any importable Python module, so that mypy's TypeInfo lookup fails when the
    plugin tries to apply the projection.  This exercises the _lookup_typeinfos
    error path without violating the schema.

    The ghost runtime_class uses the same naming convention (provider suffix →
    parent_class suffix) but lives in the same nonexistent module, so it does not
    pollute external_runtime_classes (unprojected_runtime_mro is empty).
    """
    ghost_runtime_class = ghost_provider.replace(".ParentMethods", ".parent_class")
    return ProviderProjection(
        provider=ghost_provider,
        role="parent",
        runtime_class=ghost_runtime_class,
        runtime_bases=(),
        runtime_mro=(ghost_runtime_class,),
        provider_mro=(ghost_provider,),
        provider_bases=(),
        unprojected_runtime_mro=(),
    )


def test_false_provider_base_reference_is_detected_by_plugin(tmp_path: Path) -> None:
    """Phase 8: manifest with a ghost provider_base → plugin reports missing symbol.

    A valid projection manifest is augmented with a ghost ProviderProjection for a
    class that does not exist in Python, then that ghost provider is added to the
    provider_bases of BottomCategory.ParentMethods.

    The manifest schema is satisfied (closed-world: every referenced provider is
    declared).  But when mypy runs, the plugin tries to resolve the ghost's TypeInfo
    via ctx.api.lookup_fully_qualified_or_none → returns None → plugin emits
    "provider_bases references missing symbols" instead of silently skipping.

    This proves there is no "ignore missing bases" fallback in _lookup_typeinfos.
    """
    category_fullnames = list(BASE_CATEGORY_FULLNAMES)
    category_fullnames.extend(BEHAVIOR_CASES["valid"][1:])
    projections: dict[str, ProviderProjection] = dict(
        provider_projections_for_categories(
            tuple(category_fullnames),
            roles=("parent",),
        )
    )

    # Add a ghost projection so the schema's closed-world reference check passes.
    ghost_provider = "tests.fixtures.phantom.GhostCategory.ParentMethods"
    projections[ghost_provider] = _ghost_provider_projection(ghost_provider)

    # Inject the ghost into provider_bases and provider_mro of BottomCategory.
    # The schema requires provider_bases ⊆ provider_mro[1:], so both must be updated.
    bottom_provider = (
        "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods"
    )
    original = projections[bottom_provider]
    projections[bottom_provider] = original.model_copy(
        update={
            "provider_bases": (*original.provider_bases, ghost_provider),
            "provider_mro": (*original.provider_mro, ghost_provider),
        }
    )

    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            tuple(projections.values()),
        ),
    )
    manifest_path = tmp_path / "corrupted-bases-manifest.json"
    config_path = tmp_path / "mypy.ini"
    write_manifest(manifest_path, manifest)
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )

    # Include diamond_runtime as a root source so mypy does not silence its errors.
    # Pytest adds the project root to sys.path (pythonpath = ["."]), which causes
    # mypy to treat project files as site-packages and silence them unless they are
    # root sources (follow_imports forces "normal" for root_source=True).
    diamond_runtime_module = "tests.fixtures.invariant_core.diamond_runtime"
    result = _run_mypy(
        (BEHAVIOR_CASES["valid"][0], diamond_runtime_module),
        config_path,
        tmp_path,
    )

    # The plugin must report the missing TypeInfo rather than silently skip it
    assert any(
        "provider_bases references missing symbols" in e for e in result.errors
    ), (
        f"Expected 'provider_bases references missing symbols' error for ghost manifest; "
        f"got: {result.errors}"
    )


def test_false_provider_mro_entry_is_detected_by_plugin(tmp_path: Path) -> None:
    """Phase 8: manifest with a ghost provider_mro entry → plugin reports missing symbol.

    A valid projection manifest is augmented with a ghost ProviderProjection for a
    class that does not exist in Python, then that ghost provider is added to the
    provider_mro of BottomCategory.ParentMethods (but NOT provider_bases, so the
    bases check succeeds and the MRO check is reached).

    The manifest schema is satisfied (closed-world).  But when mypy runs, the plugin
    resolves provider_bases successfully, then tries to resolve provider_mro and fails
    on the ghost → "provider_mro references missing symbols".

    This proves there is no "skip unknown MRO entries" fallback in _lookup_typeinfos.
    """
    category_fullnames = list(BASE_CATEGORY_FULLNAMES)
    category_fullnames.extend(BEHAVIOR_CASES["valid"][1:])
    projections: dict[str, ProviderProjection] = dict(
        provider_projections_for_categories(
            tuple(category_fullnames),
            roles=("parent",),
        )
    )

    # Add a ghost projection so the schema's closed-world reference check passes.
    ghost_provider = "tests.fixtures.phantom.GhostMroCategory.ParentMethods"
    projections[ghost_provider] = _ghost_provider_projection(ghost_provider)

    # Inject the ghost into provider_mro only (not provider_bases).
    # The plugin checks bases first; since bases are unchanged, that check passes,
    # and then the MRO lookup for the ghost fails.
    bottom_provider = (
        "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods"
    )
    original = projections[bottom_provider]
    projections[bottom_provider] = original.model_copy(
        update={"provider_mro": (*original.provider_mro, ghost_provider)}
    )

    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            tuple(projections.values()),
        ),
    )
    manifest_path = tmp_path / "corrupted-mro-manifest.json"
    config_path = tmp_path / "mypy.ini"
    write_manifest(manifest_path, manifest)
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )

    # Include diamond_runtime as a root source — see the provider_bases test for
    # the full explanation of why this is required in the pytest environment.
    diamond_runtime_module = "tests.fixtures.invariant_core.diamond_runtime"
    result = _run_mypy(
        (BEHAVIOR_CASES["valid"][0], diamond_runtime_module),
        config_path,
        tmp_path,
    )

    # The plugin must report the missing TypeInfo rather than silently skip it
    assert any(
        "provider_mro references missing symbols" in e for e in result.errors
    ), (
        f"Expected 'provider_mro references missing symbols' error for ghost manifest; "
        f"got: {result.errors}"
    )


def _write_plugin_config(tmp_path: Path) -> Path:
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    return config_path


def _write_axiom_plugin_config(
    tmp_path: Path,
    *,
    visible_sage_stubs: Path,
) -> Path:
    category_fullnames = [
        AXIOM_ROOT_CATEGORY,
        *(case[1] for case in AXIOM_BEHAVIOR_CASES.values()),
    ]
    projections = provider_projections_for_categories(
        tuple(category_fullnames),
        roles=("parent",),
    )
    source_modules = (
        _source_module_record(
            "tests.fixtures.invariant_core.axioms",
            FIXTURE_ROOT / "axioms.py",
        ),
        *(
            _source_module_record(case[0], _module_path(case[0]))
            for case in AXIOM_BEHAVIOR_CASES.values()
        ),
        _source_module_record(
            "sage.categories.finite_sets",
            visible_sage_stubs / "sage" / "categories" / "finite_sets.pyi",
        ),
        _source_module_record(
            "sage.categories.sets_cat",
            visible_sage_stubs / "sage" / "categories" / "sets_cat.pyi",
        ),
        _source_module_record(
            "sage.categories.sets_with_partial_maps",
            visible_sage_stubs
            / "sage"
            / "categories"
            / "sets_with_partial_maps.pyi",
        ),
        _source_module_record(
            "sage.categories.objects",
            visible_sage_stubs / "sage" / "categories" / "objects.pyi",
        ),
    )
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            tuple(projections.values()),
            source_modules=source_modules,
        ),
        source_modules=source_modules,
    )
    manifest_path = tmp_path / "sage-category-axiom-behavior-projections.json"
    config_path = tmp_path / "axiom-behavior-mypy.ini"
    write_manifest(manifest_path, manifest)
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )
    return config_path


def _run_nested_provider_mypy(
    tmp_path: Path,
    *,
    with_plugin: bool,
) -> BuildResult:
    source_root = tmp_path / "nested-providers"
    axiom_projections = provider_projections_for_categories(
        (COMMUTATIVE_RINGS_CATEGORY,),
        roles=("parent",),
    )
    functorial_projections = provider_projections_for_categories(
        (FUNCTORIAL_CARTESIAN_CATEGORY,),
        roles=("parent",),
    )
    parameterized_projections = provider_projections_for_categories(
        PARAMETERIZED_CATEGORY_FULLNAMES,
        roles=("parent",),
    )
    projections = {
        **axiom_projections,
        **functorial_projections,
        **parameterized_projections,
    }
    source_modules = _write_nested_provider_sources(
        source_root,
        projections=tuple(projections.values()),
    )
    config_path = tmp_path / "nested-provider-mypy.ini"
    manifest_path = tmp_path / "nested-provider-manifest.json"
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            tuple(projections.values()),
            source_modules=source_modules,
        ),
        source_modules=source_modules,
    )
    write_manifest(manifest_path, manifest)
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )

    options = Options()
    options.incremental = False
    options.cache_dir = str(tmp_path / f"{with_plugin}-mypy-cache")
    options.mypy_path = [str(source_root)]
    options.ignore_missing_imports = True
    if with_plugin:
        options.config_file = str(config_path)
        options.plugins = ["sage_mypy_category_plugin.plugin"]
    return build(
        sources=[
            BuildSource(
                str(source_root / "sage" / "categories" / "commutative_rings.py"),
                "sage.categories.commutative_rings",
                None,
            ),
            BuildSource(
                str(source_root / "sage" / "categories" / "sets_cat.py"),
                "sage.categories.sets_cat",
                None,
            ),
            BuildSource(
                str(source_root / "sage" / "categories" / "vector_spaces.py"),
                "sage.categories.vector_spaces",
                None,
            ),
        ],
        options=options,
    )


def _write_nested_provider_sources(
    source_root: Path,
    *,
    projections: tuple[ProviderProjection, ...],
) -> tuple[SourceModuleRecord, ...]:
    module_trees: dict[str, SourceTree] = defaultdict(dict)
    for fullname in _projection_fullnames(projections):
        if fullname == "builtins.object":
            continue
        module_name, qualname = _importable_module_and_qualname(fullname)
        _add_qualname(module_trees[module_name], qualname)

    method_bodies = {
        _importable_module_and_qualname(RINGS_PROVIDER): (
            "def is_commutative(self) -> bool:",
            "    return False",
        ),
        _importable_module_and_qualname(SETS_PROVIDER): (
            "def construction(self) -> str:",
            '    return "sets"',
        ),
        _importable_module_and_qualname(MODULES_PROVIDER): (
            "def tensor_square(self) -> str:",
            '    return "module tensor square"',
        ),
        _importable_module_and_qualname(COMMUTATIVE_RINGS_PROVIDER): (
            "@override",
            "def is_commutative(self) -> bool:",
            "    return True",
            "",
            "@override",
            "def not_a_sage_axiom_method(self) -> bool:",
            "    return True",
        ),
        _importable_module_and_qualname(FUNCTORIAL_CARTESIAN_PARENT_PROVIDER): (
            "@override",
            "def construction(self) -> str:",
            '    return "cartesian products"',
            "",
            "@override",
            "def not_a_sage_functorial_method(self) -> str:",
            '    return "invalid"',
        ),
        _importable_module_and_qualname(VECTOR_SPACES_PROVIDER): (
            "@override",
            "def tensor_square(self) -> str:",
            '    return "vector space tensor square"',
            "",
            "@override",
            "def not_a_sage_parameterized_method(self) -> str:",
            '    return "invalid"',
        ),
    }
    source_modules: list[SourceModuleRecord] = []
    for package_dir in (
        source_root / "sage",
        source_root / "sage" / "categories",
    ):
        package_dir.mkdir(parents=True, exist_ok=True)
        (package_dir / "__init__.py").write_text("")

    for module_name, tree in sorted(module_trees.items()):
        path = source_root.joinpath(*module_name.split(".")).with_suffix(".py")
        path.parent.mkdir(parents=True, exist_ok=True)
        source = "\n".join(
            (
                "from typing import override",
                "",
                *_source_lines(tree, method_bodies, module_name=module_name),
            )
        )
        path.write_text(source + "\n")
        source_bytes = path.read_bytes()
        source_stat = path.stat()
        source_modules.append(
            SourceModuleRecord(
                module=module_name,
                path=str(path),
                sha256=sha256(source_bytes).hexdigest(),
                mtime_ns=source_stat.st_mtime_ns,
            )
        )
    return tuple(source_modules)


def _projection_fullnames(
    projections: tuple[ProviderProjection, ...],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            fullname
            for projection in projections
            for fullname in (
                projection.provider,
                projection.runtime_class,
                *projection.runtime_bases,
                *projection.runtime_mro,
                *projection.provider_bases,
                *projection.provider_mro,
                *projection.unprojected_runtime_mro,
            )
        )
    )


def _importable_module_and_qualname(fullname: str) -> tuple[str, tuple[str, ...]]:
    parts = fullname.split(".")
    for split_index in range(len(parts), 0, -1):
        module_name = ".".join(parts[:split_index])
        try:
            import_module(module_name)
        except ModuleNotFoundError:
            continue
        return module_name, tuple(parts[split_index:])
    raise AssertionError(f"Could not find importable module for {fullname!r}")


def _add_qualname(tree: SourceTree, qualname: tuple[str, ...]) -> None:
    current = tree
    for name in qualname:
        current = current.setdefault(name, {})


def _source_lines(
    tree: SourceTree,
    method_bodies: dict[tuple[str, tuple[str, ...]], tuple[str, ...]],
    *,
    module_name: str | None = None,
    qualname: tuple[str, ...] = (),
    indent: int = 0,
) -> tuple[str, ...]:
    lines: list[str] = []
    for name, child in sorted(
        tree.items(),
        key=lambda item: (item[0] != "ParentMethods", item[0]),
    ):
        nested_qualname = (*qualname, name)
        lines.append(f"{'    ' * indent}class {name}:")
        if child:
            lines.extend(
                _source_lines(
                    child,
                    method_bodies,
                    module_name=module_name,
                    qualname=nested_qualname,
                    indent=indent + 1,
                )
            )
            continue

        body = method_bodies.get((module_name or "", nested_qualname), ("pass",))
        lines.extend(f"{'    ' * (indent + 1)}{line}" for line in body)
    return tuple(lines)


def _run_mypy(
    modules: tuple[str, ...],
    config_path: Path,
    tmp_path: Path,
    *,
    mypy_path_entries: tuple[Path, ...] = (REPO_ROOT,),
) -> BuildResult:
    options = _options(tmp_path)
    options.config_file = str(config_path)
    options.plugins = ["sage_mypy_category_plugin.plugin"]
    options.mypy_path = [str(path) for path in mypy_path_entries]
    return build(sources=[_source(module) for module in modules], options=options)


def _run_mypy_without_plugin(
    modules: tuple[str, ...],
    tmp_path: Path,
    *,
    mypy_path_entries: tuple[Path, ...] = (REPO_ROOT,),
) -> BuildResult:
    options = _options(tmp_path)
    options.mypy_path = [str(path) for path in mypy_path_entries]
    return build(sources=[_source(module) for module in modules], options=options)


def _options(tmp_path: Path) -> Options:
    options = Options()
    options.incremental = False
    options.cache_dir = str(tmp_path / "mypy-cache")
    options.enable_error_code = ["explicit-override"]
    options.mypy_path = [str(REPO_ROOT)]
    options.ignore_missing_imports = True
    return options


def _source(module: str) -> BuildSource:
    return BuildSource(str(_module_path(module)), module, None)


def _module_path(module: str) -> Path:
    filename = module.rsplit(".", maxsplit=1)[-1] + ".py"
    return FIXTURE_ROOT / filename


def _run_mypy_with_sources(
    sources: tuple[BuildSource, ...],
    config_path: Path,
    tmp_path: Path,
    *,
    mypy_path_entries: tuple[Path, ...] = (REPO_ROOT,),
) -> BuildResult:
    """Like _run_mypy but accepts explicit BuildSource objects instead of module names.

    Used for categories outside FIXTURE_ROOT (e.g. tests/real_categories/).
    """
    options = _options(tmp_path)
    options.config_file = str(config_path)
    options.plugins = ["sage_mypy_category_plugin.plugin"]
    options.mypy_path = [str(path) for path in mypy_path_entries]
    return build(sources=list(sources), options=options)


def _run_mypy_without_plugin_with_sources(
    sources: tuple[BuildSource, ...],
    tmp_path: Path,
    *,
    mypy_path_entries: tuple[Path, ...] = (REPO_ROOT,),
) -> BuildResult:
    """Like _run_mypy_without_plugin but accepts explicit BuildSource objects."""
    options = _options(tmp_path)
    options.mypy_path = [str(path) for path in mypy_path_entries]
    return build(sources=list(sources), options=options)


def _write_visible_sage_axiom_stubs(tmp_path: Path) -> Path:
    stub_root = tmp_path / "visible-sage-axiom-stubs"
    categories = stub_root / "sage" / "categories"
    categories.mkdir(parents=True)
    (stub_root / "sage" / "__init__.pyi").write_text("")
    (categories / "__init__.pyi").write_text("")
    (categories / "finite_sets.pyi").write_text(
        "\n".join(
            (
                "class FiniteSets:",
                "    class ParentMethods: ...",
                "",
            )
        )
    )
    (categories / "sets_cat.pyi").write_text(
        "\n".join(
            (
                "class Sets:",
                "    class ParentMethods: ...",
                "",
            )
        )
    )
    (categories / "sets_with_partial_maps.pyi").write_text(
        "\n".join(
            (
                "class SetsWithPartialMaps:",
                "    class ParentMethods: ...",
                "",
            )
        )
    )
    (categories / "objects.pyi").write_text(
        "\n".join(
            (
                "class Objects:",
                "    class ParentMethods: ...",
                "",
            )
        )
    )
    return stub_root


def _source_module_record(module_name: str, path: Path) -> SourceModuleRecord:
    source_bytes = path.read_bytes()
    source_stat = path.stat()
    return SourceModuleRecord(
        module=module_name,
        path=str(path),
        sha256=sha256(source_bytes).hexdigest(),
        mtime_ns=source_stat.st_mtime_ns,
    )


def _case_contains(result: BuildResult, case_name: str, fragment: str) -> bool:
    return any(fragment in error for error in _case_errors(result, case_name))


def _case_contains_fragments(
    result: BuildResult,
    case_name: str,
    *fragments: str,
) -> bool:
    return any(
        all(fragment in error for fragment in fragments)
        for error in _case_errors(result, case_name)
    )


def _contains_error(result: BuildResult, fragment: str) -> bool:
    return any(fragment in error for error in result.errors)


def _contains_error_fragments(result: BuildResult, *fragments: str) -> bool:
    return any(
        all(fragment in error for fragment in fragments)
        for error in result.errors
    )


def _case_errors(result: BuildResult, case_name: str) -> tuple[str, ...]:
    filename = _module_path(_behavior_case_module(case_name)).name
    return tuple(error for error in result.errors if filename in error)


def _behavior_case_module(case_name: str) -> str:
    if case_name in BEHAVIOR_CASES:
        return BEHAVIOR_CASES[case_name][0]
    assert case_name in AXIOM_BEHAVIOR_CASES, f"Unknown behavior case {case_name!r}"
    return AXIOM_BEHAVIOR_CASES[case_name][0]
