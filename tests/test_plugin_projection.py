from __future__ import annotations

import json
from collections.abc import Sequence
from functools import cache
from hashlib import sha256
from importlib import import_module
from pathlib import Path

import pytest
from mypy.build import BuildResult, build
from mypy.errors import CompileError
from mypy.modulefinder import BuildSource
from mypy.nodes import TypeInfo
from mypy.options import Options

from sage_mypy_category_plugin.manifest import (
    ProjectionManifest,
    SourceModuleRecord,
    load_manifest,
    write_manifest,
)
from sage_mypy_category_plugin.oracle import (
    provider_projections_for_categories,
)
from sage_mypy_category_plugin.plugin import (
    CONFIG_SECTION,
    SageCategoryProjectionPlugin,
    _normalize_role_name,
    _source_modules_stale_reason,
)
from sage_mypy_category_plugin.projection import ProviderProjection, ProviderRole
from tests.manifest_helpers import external_runtime_class_records_for_test_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_MODULE = "tests.fixtures.invariant_core.diamond_runtime"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "invariant_core" / "diamond_runtime.py"
CATEGORY_FULLNAMES = (
    f"{FIXTURE_MODULE}.TopCategory",
    f"{FIXTURE_MODULE}.LeftCategory",
    f"{FIXTURE_MODULE}.RightCategory",
    f"{FIXTURE_MODULE}.BottomCategory",
)
BOTTOM_PROVIDER = f"{FIXTURE_MODULE}.BottomCategory.ParentMethods"
CATEGORY_BEHAVIOR_BASE_MODULE = (
    "tests.fixtures.invariant_core.diamond_behavior_decorated_base"
)
CATEGORY_BEHAVIOR_PROJECTION_MODULE = (
    "tests.fixtures.invariant_core.diamond_behavior_decorated_projection"
)
CATEGORY_BEHAVIOR_BASE_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "invariant_core"
    / "diamond_behavior_decorated_base.py"
)
CATEGORY_BEHAVIOR_PROJECTION_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "invariant_core"
    / "diamond_behavior_decorated_projection.py"
)
CATEGORY_BEHAVIOR_FULLNAMES = (
    f"{CATEGORY_BEHAVIOR_BASE_MODULE}.DecoratedBaseCategory",
    f"{CATEGORY_BEHAVIOR_PROJECTION_MODULE}.DecoratedProjectionCategory",
)
CATEGORY_BEHAVIOR_PROVIDERS = tuple(
    f"{fullname}.ParentMethods" for fullname in CATEGORY_BEHAVIOR_FULLNAMES
)
CATEGORY_SPECS_LIKE_ROOT_MODULE = (
    "tests.fixtures.invariant_core.category_specs_like.rings"
)
CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE = (
    "tests.fixtures.invariant_core.category_specs_like.rings.subcategories.commutative"
)
CATEGORY_SPECS_LIKE_SUBCATEGORY_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "invariant_core"
    / "category_specs_like"
    / "rings"
    / "subcategories"
    / "commutative.py"
)
CATEGORY_SPECS_LIKE_FULLNAMES = (
    f"{CATEGORY_SPECS_LIKE_ROOT_MODULE}.Rings",
    f"{CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE}._CommutativeRings",
)
CATEGORY_SPECS_LIKE_ROOT_PROVIDER = (
    f"{CATEGORY_SPECS_LIKE_ROOT_MODULE}._RingObjectMethods"
)
CATEGORY_SPECS_LIKE_COMMUTATIVE_PROVIDER = (
    f"{CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE}._CommutativeRings.ParentMethods"
)
PROVIDER_ROLES_MODULE = "tests.fixtures.invariant_core.provider_roles.diamond"
PROVIDER_ROLES_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "invariant_core" / "provider_roles" / "diamond.py"
)
PROVIDER_ROLES_FULLNAMES = (
    f"{PROVIDER_ROLES_MODULE}.TopCategory",
    f"{PROVIDER_ROLES_MODULE}.LeftCategory",
    f"{PROVIDER_ROLES_MODULE}.RightCategory",
    f"{PROVIDER_ROLES_MODULE}.BottomCategory",
)
HOMSET_ROLES_MODULE = "tests.fixtures.invariant_core.provider_roles.homsets"
HOMSET_ROLES_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "invariant_core" / "provider_roles" / "homsets.py"
)
HOMSET_ROLES_FULLNAMES = (
    f"{HOMSET_ROLES_MODULE}.BottomCategory",
    f"{HOMSET_ROLES_MODULE}.RefinedSharedHomsetProviderCategory",
)
REFINED_SHARED_HOMSET_PARENT_PROVIDER = (
    f"{HOMSET_ROLES_MODULE}.RefinedSharedHomsetProviderCategory."
    "Homsets.ParentMethods"
)
SHARED_HOMSET_PARENT_PROVIDER = f"{HOMSET_ROLES_MODULE}.SharedHomsetParentMethods"
AXIOM_FIXTURE_MODULE = "tests.fixtures.invariant_core.axioms"
AXIOM_FIXTURE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "invariant_core" / "axioms.py"
)
NESTED_AXIOM_FULLNAMES = (
    f"{AXIOM_FIXTURE_MODULE}.AxiomRootCategory.Finite",
)
NESTED_AXIOM_PROVIDER = f"{NESTED_AXIOM_FULLNAMES[0]}.ParentMethods"
LINKED_AXIOM_ROOT_MODULE = "tests.fixtures.invariant_core.linked_axiom_root"
LINKED_AXIOM_ROOT_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "invariant_core" / "linked_axiom_root.py"
)
LINKED_AXIOM_FINITE_MODULE = "tests.fixtures.invariant_core.linked_axiom_finite"
LINKED_AXIOM_FINITE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "invariant_core" / "linked_axiom_finite.py"
)
LINKED_AXIOM_FULLNAMES = (
    f"{LINKED_AXIOM_ROOT_MODULE}.LinkedAxiomRootCategory.Finite",
)
LINKED_AXIOM_PROVIDER = (
    f"{LINKED_AXIOM_FINITE_MODULE}.LinkedFiniteAxiomCategory.ParentMethods"
)
COMMUTATIVE_RINGS_CATEGORY = "sage.categories.commutative_rings.CommutativeRings"
COMMUTATIVE_RINGS_PROVIDER = (
    "sage.categories.commutative_rings.CommutativeRings.ParentMethods"
)
FUNCTORIAL_CARTESIAN_CATEGORY = (
    "tests.fixtures.invariant_core.functorial.cartesian_products."
    "CartesianProductsCategory"
)
FUNCTORIAL_CARTESIAN_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "invariant_core"
    / "functorial"
    / "cartesian_products.py"
)
FUNCTORIAL_CARTESIAN_MODULE = (
    "tests.fixtures.invariant_core.functorial.cartesian_products"
)
FUNCTORIAL_CARTESIAN_PARENT_PROVIDER = (
    "sage.categories.sets_cat.Sets.CartesianProducts.ParentMethods"
)
FUNCTORIAL_CARTESIAN_ELEMENT_PROVIDER = (
    "sage.categories.sets_cat.Sets.CartesianProducts.ElementMethods"
)
FUNCTORIAL_TENSOR_CATEGORY = (
    "tests.fixtures.invariant_core.functorial.tensor_products."
    "TensorProductsCategory"
)
FUNCTORIAL_TENSOR_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "invariant_core"
    / "functorial"
    / "tensor_products.py"
)
FUNCTORIAL_TENSOR_MODULE = "tests.fixtures.invariant_core.functorial.tensor_products"
FUNCTORIAL_TENSOR_PARENT_PROVIDER = (
    "sage.categories.modules.Modules.TensorProducts.ParentMethods"
)
PARAMETERIZED_CATEGORY_FULLNAMES = (
    "tests.fixtures.invariant_core.parameterized.ModulesOverIntegers",
    "tests.fixtures.invariant_core.parameterized.ModulesOverRationals",
    "tests.fixtures.invariant_core.parameterized.VectorSpacesOverRationals",
)
PARAMETERIZED_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "invariant_core" / "parameterized.py"
)
PARAMETERIZED_MODULE = "tests.fixtures.invariant_core.parameterized"
PARAMETERIZED_MODULES_PROVIDER = "sage.categories.modules.Modules.ParentMethods"
PARAMETERIZED_VECTOR_SPACES_PROVIDER = (
    "sage.categories.vector_spaces.VectorSpaces.ParentMethods"
)
DIAMOND_SOURCE_MODULE = SourceModuleRecord(
    module=FIXTURE_MODULE,
    path="tests/fixtures/invariant_core/diamond_runtime.py",
    sha256=sha256(FIXTURE_PATH.read_bytes()).hexdigest(),
    mtime_ns=FIXTURE_PATH.stat().st_mtime_ns,
)


def _provider_projections(
    category_fullnames: tuple[str, ...],
    *,
    roles: tuple[ProviderRole, ...],
) -> dict[str, ProviderProjection]:
    return dict(_provider_projection_items(category_fullnames, roles))




@cache
def _provider_projection_items(
    category_fullnames: tuple[str, ...],
    roles: tuple[ProviderRole, ...],
) -> tuple[tuple[str, ProviderProjection], ...]:
    return tuple(
        provider_projections_for_categories(category_fullnames, roles=roles).items()
    )
















def test_plugin_reports_semantic_manifest_config_data(tmp_path: Path) -> None:
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )

    options = Options()
    options.config_file = str(config_path)
    plugin = SageCategoryProjectionPlugin(options)
    config_data = plugin.report_config_data(
        ctx=None,  # type: ignore[arg-type]
    )
    manifest = load_manifest(cache_dir / "projection-manifest.json")

    assert config_data["manifest_semantic_projection_digest"] == (
        manifest.semantic_projection_digest
    )
    assert config_data["manifest_plugin_schema_version"] == (
        manifest.plugin_schema_version
    )
    assert config_data["manifest_sage_version"] == manifest.sage_version
    assert config_data["manifest_sage_git_revision"] == (
        manifest.sage_git_revision or ""
    )
    assert config_data["manifest_mypy_min_version"] == manifest.mypy_min_version
    assert config_data["manifest_mypy_max_version"] == manifest.mypy_max_version
    assert config_data["manifest_source_module_digest"] == (
        manifest.source_module_digest
    )
    assert FIXTURE_MODULE in manifest.source_module_by_module


def test_stale_reason_detects_missing_file(tmp_path: Path) -> None:
    """_source_modules_stale_reason returns the 'file is missing' diagnostic.

    Package-mode plugin init regenerates a missing cache before validating it, so
    the file-missing branch is tested directly against the owned stale-detection
    logic.
    """
    missing_path = tmp_path / "gone.py"
    # Never created — simulates a deleted source file.
    record = SourceModuleRecord(
        module="some.source.module",
        path=str(missing_path),
        sha256="a" * 64,
        mtime_ns=1_000_000_000,
    )
    reason = _source_modules_stale_reason((record,))
    assert reason == (
        "Stale Sage category source module metadata for "
        "some.source.module: file is missing"
    ), reason


def test_stale_reason_detects_mtime_mismatch(tmp_path: Path) -> None:
    """_source_modules_stale_reason returns the mtime_ns-mismatch diagnostic.

    The sha256-mismatch branch is exercised through the full plugin integration
    test (test_plugin_fails_clearly_for_stale_source_module_metadata).  The
    mtime_ns branch is only reachable when the file exists but has been touched;
    testing it directly against the detection function keeps the integration test
    fast and the unit test precise.
    """
    source_path = tmp_path / "source.py"
    source_path.write_text("x = 1\n")
    real_mtime_ns = source_path.stat().st_mtime_ns
    stale_mtime_ns = real_mtime_ns - 1  # one nanosecond behind
    record = SourceModuleRecord(
        module="some.source.module",
        path=str(source_path),
        sha256="a" * 64,
        mtime_ns=stale_mtime_ns,
    )
    reason = _source_modules_stale_reason((record,))
    assert reason is not None
    assert "mtime_ns mismatch" in reason, reason
    assert "some.source.module" in reason, reason


def test_plugin_fails_clearly_when_packages_option_is_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)

    with pytest.raises(CompileError) as raised:
        SageCategoryProjectionPlugin(options)

    assert raised.value.messages == [
        f"[{CONFIG_SECTION}] section in {config_path} must specify 'packages'"
    ]


def test_normalize_role_name_maps_all_documented_variants_to_canonical_literals() -> None:
    """_normalize_role_name must accept every documented user-facing variant.

    The plugin config accepts multiple spellings of homset roles because users
    copying from examples may use spaces or CamelCase.  A missing or misspelled
    entry in the role_map would silently pass through and then fail in _parse_roles
    with an opaque "Invalid role" error instead of the correct canonical form.
    """
    # Canonical forms map to themselves
    assert _normalize_role_name("parent") == "parent"
    assert _normalize_role_name("element") == "element"
    assert _normalize_role_name("subcategory") == "subcategory"
    assert _normalize_role_name("morphism") == "morphism"
    assert _normalize_role_name("homset_parent") == "homset_parent"
    assert _normalize_role_name("homset_element") == "homset_element"

    # Space-separated variants: common in hand-written INI files
    assert _normalize_role_name("homset parent") == "homset_parent"
    assert _normalize_role_name("homset element") == "homset_element"

    # No-separator camelCase-like variants
    assert _normalize_role_name("homsetparent") == "homset_parent"
    assert _normalize_role_name("homsetelement") == "homset_element"

    # Case insensitive (lowercasing happens before map lookup)
    assert _normalize_role_name("Parent") == "parent"
    assert _normalize_role_name("PARENT") == "parent"
    assert _normalize_role_name("HomsetParent") == "homset_parent"
    assert _normalize_role_name("Homset Parent") == "homset_parent"

    # Unknown names pass through unchanged so _parse_roles can produce a clear error
    assert _normalize_role_name("badrolename") == "badrolename"
    assert _normalize_role_name("") == ""


def test_plugin_fails_clearly_for_invalid_role_config(tmp_path: Path) -> None:
    """Plugin must reject unrecognised role strings in the config with a clear error.

    The role list in mypy.ini is user-controlled; a typo or unsupported role
    string must produce an actionable CompileError rather than silently falling
    back to no projection or mapping to the wrong role.
    """
    cache_dir = tmp_path / "cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                f"[{CONFIG_SECTION}]",
                "packages = tests.fixtures.invariant_core.diamond_runtime",
                "roles = badrolename",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)

    with pytest.raises(CompileError) as raised:
        SageCategoryProjectionPlugin(options)

    assert any("badrolename" in msg for msg in raised.value.messages), (
        "Expected CompileError to name the invalid role 'badrolename'; "
        f"got messages: {raised.value.messages}"
    )


def test_plugin_config_parser_strips_inline_comments(tmp_path: Path) -> None:
    """_parse_multiline_option must strip inline # comments from config values.

    Inline comments are documented as valid in the [sage-mypy-category-plugin]
    section.  If stripping were broken, the package or role string would include
    the comment text and discovery / role parsing would fail.
    """
    cache_dir = tmp_path / "cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                f"[{CONFIG_SECTION}]",
                "packages =",
                # Inline comment after the package name — must be stripped.
                "    tests.fixtures.invariant_core.diamond_runtime  # diamond fixture",
                "roles =",
                "    parent  # the parent provider role",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)

    # The plugin must start without error: comments are stripped, package and
    # role names are clean.  If the package string retained " # diamond fixture",
    # discover_category_fullnames would fail or return empty and raise CompileError.
    plugin = SageCategoryProjectionPlugin(options)
    assert FIXTURE_MODULE in plugin._source_modules, (
        "diamond_runtime fixture must appear as a source module — "
        "comment stripping likely failed if the plugin raised CompileError above"
    )
    # parent role only — element/homset providers must not appear in projections.
    assert all(
        ".ParentMethods" in provider or ".parent_class" in provider
        for provider in plugin._projection_by_provider
    ), "Only parent-role providers expected when roles = parent"


def test_plugin_passthrough_when_no_config_section(tmp_path: Path) -> None:
    """Plugin listed in [mypy] plugins but no [sage-mypy-category-plugin] section.

    Proves that an unconfigured plugin is a safe no-op: no CompileError, no
    projections, no stubs.  Needed so global mypy configs can list the plugin
    without requiring every project to configure it.
    """
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)

    plugin = SageCategoryProjectionPlugin(options)

    # Passthrough: no projections, no manifest path, no stubs
    assert plugin._projection_by_provider == {}
    assert plugin._manifest_path is None
    assert plugin._manifest.projections == ()
    assert plugin.get_customize_class_mro_hook("any.fullname") is None
    assert plugin.report_config_data(None) == {"passthrough": "true"}  # type: ignore[arg-type]


def test_plugin_fails_clearly_when_no_categories_found_in_packages(
    tmp_path: Path,
) -> None:
    """Plugin must report a clear error when the configured packages yield no categories.

    Covers the 'no category classes found' branch in _generate_and_cache.
    tests.fixtures.invariant_core.local_wrapper defines LocalCategoryBase whose
    super_categories is still abstract (not overridden), so discover_category_fullnames
    returns an empty tuple and the plugin cannot proceed.
    """
    cache_dir = tmp_path / "cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                f"[{CONFIG_SECTION}]",
                "packages = tests.fixtures.invariant_core.local_wrapper",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)

    with pytest.raises(CompileError) as raised:
        SageCategoryProjectionPlugin(options)

    assert any(
        "No Sage category classes found" in msg for msg in raised.value.messages
    ), raised.value.messages


def test_plugin_generates_manifest_from_packages_config(tmp_path: Path) -> None:
    """Package config auto-generates the production projection manifest."""
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.diamond_runtime",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)
    options.ignore_missing_imports = True

    plugin = SageCategoryProjectionPlugin(options)

    # Manifest was generated
    manifest_path = cache_dir / "projection-manifest.json"
    assert manifest_path.is_file(), "Plugin should have generated manifest"
    manifest = json.loads(manifest_path.read_text())
    assert len(manifest["projections"]) == 4, "Diamond fixture has 4 categories"

    assert not (cache_dir / "stubs").exists(), (
        "Production package mode must not generate upstream Sage stubs"
    )

    # Projections are loaded correctly
    bottom_provider = (
        "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods"
    )
    assert bottom_provider in plugin._projection_by_provider


def test_package_mode_projects_category_specs_like_typeinfo_graph(
    tmp_path: Path,
) -> None:
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.category_specs_like",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )

    result = _build_fixture(
        config_path,
        tmp_path,
        fixture_path=CATEGORY_SPECS_LIKE_SUBCATEGORY_PATH,
        fixture_module=CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE,
    )
    assert result.errors == []

    manifest = load_manifest(cache_dir / "projection-manifest.json")
    projection = manifest.projection_by_provider[
        CATEGORY_SPECS_LIKE_COMMUTATIVE_PROVIDER
    ]
    info = _nested_typeinfo(
        result,
        module=CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE,
        outer="_CommutativeRings",
        inner="ParentMethods",
    )

    observed_bases = tuple(base.type.fullname for base in info.bases)
    observed_mro = tuple(mro_info.fullname for mro_info in info.mro)

    assert observed_bases == projection.provider_bases
    assert observed_mro == (*projection.provider_mro, "builtins.object")


def test_package_mode_projects_all_provider_role_typeinfo_graphs(
    tmp_path: Path,
) -> None:
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.provider_roles",
                "roles =",
                "  parent",
                "  element",
                "  subcategory",
                "  morphism",
                "  homset_parent",
                "  homset_element",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )

    result = _build_fixture(
        config_path,
        tmp_path,
        fixture_sources=(
            (PROVIDER_ROLES_PATH, PROVIDER_ROLES_MODULE),
            (HOMSET_ROLES_PATH, HOMSET_ROLES_MODULE),
        ),
    )
    assert result.errors == []

    manifest = load_manifest(cache_dir / "projection-manifest.json")
    local_module_prefixes = (PROVIDER_ROLES_MODULE, HOMSET_ROLES_MODULE)
    projections = tuple(
        projection
        for projection in manifest.projections
        if projection.provider.startswith(local_module_prefixes)
    )

    assert {projection.role for projection in projections} == {
        "element",
        "homset_element",
        "homset_parent",
        "morphism",
        "parent",
        "subcategory",
    }

    for projection in projections:
        info = _typeinfo_for_fullname(result, projection.provider)
        observed_bases = tuple(base.type.fullname for base in info.bases)
        observed_mro = tuple(mro_info.fullname for mro_info in info.mro)

        assert observed_bases == projection.provider_bases, projection.provider
        assert observed_mro == (
            *projection.provider_mro,
            "builtins.object",
        ), projection.provider


def test_cached_manifest_projects_functorial_and_parameterized_sage_typeinfo_graphs(
    tmp_path: Path,
) -> None:
    cache_dir = tmp_path / "sage-category-cache"
    manifest_path = cache_dir / "projection-manifest.json"
    projections = provider_projections_for_categories(
        (
            FUNCTORIAL_CARTESIAN_CATEGORY,
            FUNCTORIAL_TENSOR_CATEGORY,
            *PARAMETERIZED_CATEGORY_FULLNAMES,
        ),
        roles=("parent", "element"),
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
    cache_dir.mkdir(parents=True)
    write_manifest(manifest_path, manifest)

    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages =",
                "  tests.fixtures.invariant_core",
                "roles =",
                "  parent",
                "  element",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )

    result = _build_fixture(
        config_path,
        tmp_path,
        fixture_sources=(
            (FUNCTORIAL_CARTESIAN_PATH, FUNCTORIAL_CARTESIAN_MODULE),
            (FUNCTORIAL_TENSOR_PATH, FUNCTORIAL_TENSOR_MODULE),
            (PARAMETERIZED_PATH, PARAMETERIZED_MODULE),
        ),
    )
    assert not _contains_error_fragment(result, "Sage category provider projection")
    assert not _contains_error_fragment(result, "Sage category provider MRO mismatch")

    manifest = load_manifest(manifest_path)
    provider_fullnames = (
        FUNCTORIAL_CARTESIAN_PARENT_PROVIDER,
        FUNCTORIAL_CARTESIAN_ELEMENT_PROVIDER,
        FUNCTORIAL_TENSOR_PARENT_PROVIDER,
        PARAMETERIZED_MODULES_PROVIDER,
        PARAMETERIZED_VECTOR_SPACES_PROVIDER,
    )

    for provider_fullname in provider_fullnames:
        projection = manifest.projection_by_provider[provider_fullname]
        info = _typeinfo_for_fullname(result, provider_fullname)
        observed_bases = tuple(base.type.fullname for base in info.bases)
        observed_mro = tuple(mro_info.fullname for mro_info in info.mro)

        assert observed_bases == projection.provider_bases, provider_fullname
        assert observed_mro == (
            *projection.provider_mro,
            "builtins.object",
        ), provider_fullname


def test_plugin_regenerates_from_clean_cache(tmp_path: Path) -> None:
    """Phase 1A: plugin init regenerates when no cache exists."""
    cache_dir = tmp_path / "sage-category-cache"
    # Ensure clean state
    assert not cache_dir.exists()

    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.diamond_runtime",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)
    options.ignore_missing_imports = True

    _plugin = SageCategoryProjectionPlugin(options)

    # Cache was created
    assert cache_dir.is_dir()
    assert (cache_dir / "projection-manifest.json").is_file()
    assert not (cache_dir / "stubs").exists()

    # Second init from same cache works (idempotency)
    _plugin2 = SageCategoryProjectionPlugin(options)
    assert (cache_dir / "projection-manifest.json").is_file()


def test_plugin_reuses_cache_on_second_init_without_regenerating(tmp_path: Path) -> None:
    """Phase 7 E2: when the cached manifest is fresh, the plugin reuses it verbatim.

    The manifest file must NOT be rewritten on a cache hit.  We verify this by
    capturing the mtime_ns of the manifest file immediately after the first init
    and asserting that it is unchanged after the second init.

    Additionally the ``semantic_projection_digest`` must be identical across both
    initialisations — proving the same projection graph was loaded both times.
    """
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.diamond_runtime",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)
    options.ignore_missing_imports = True

    # First init — cold cache, manifest is generated.
    plugin1 = SageCategoryProjectionPlugin(options)
    manifest_path = cache_dir / "projection-manifest.json"
    assert manifest_path.is_file()
    mtime_after_first_init = manifest_path.stat().st_mtime_ns
    digest_after_first_init = plugin1._manifest.semantic_projection_digest

    # Second init — cache is fresh; manifest must not be rewritten.
    plugin2 = SageCategoryProjectionPlugin(options)
    mtime_after_second_init = manifest_path.stat().st_mtime_ns

    assert mtime_after_second_init == mtime_after_first_init, (
        "Manifest was rewritten on cache hit — plugin regenerated unnecessarily"
    )
    assert plugin2._manifest.semantic_projection_digest == digest_after_first_init, (
        "semantic_projection_digest changed across cache-hit inits — projection graph drifted"
    )


def test_plugin_detects_stale_source_and_regenerates_in_packages_mode(
    tmp_path: Path,
) -> None:
    """Phase 7 E3: mutating a source file triggers cache invalidation and regeneration.

    When a provider source file's mtime_ns changes after the manifest was generated,
    ``_try_load_cached_manifest`` must detect the staleness and return None, causing
    the plugin to regenerate the manifest without raising a CompileError.

    The test bumps the fixture source file's mtime by 1 ns to simulate a save, then
    restores it in a try/finally to leave the repo directory unmodified.
    """
    import os

    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.diamond_runtime",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)
    options.ignore_missing_imports = True

    # First init — cold cache, manifest generated.
    SageCategoryProjectionPlugin(options)
    manifest_path = cache_dir / "projection-manifest.json"
    assert manifest_path.is_file()
    mtime_after_first_init = manifest_path.stat().st_mtime_ns

    # Identify a tracked source module (the fixture package __init__ or first .py).
    manifest = load_manifest(manifest_path)
    tracked_paths = [
        Path(record.path)
        for record in manifest.source_modules
        if Path(record.path).suffix == ".py" and Path(record.path).exists()
    ]
    assert tracked_paths, "Manifest must track at least one .py source module"
    source_to_touch = tracked_paths[0]
    original_stat = source_to_touch.stat()
    original_atime = original_stat.st_atime_ns
    original_mtime = original_stat.st_mtime_ns

    # Bump mtime_ns by 1 ns — simulates a file save without changing content.
    try:
        os.utime(
            source_to_touch,
            ns=(original_atime, original_mtime + 1),
        )

        # Second init — stale source detected → manifest regenerated.
        SageCategoryProjectionPlugin(options)
        mtime_after_second_init = manifest_path.stat().st_mtime_ns

        assert mtime_after_second_init > mtime_after_first_init, (
            "Manifest mtime did not advance after stale-source regeneration — "
            "plugin failed to detect the source mutation and regenerate"
        )
    finally:
        # Restore the original mtime so the repo is not dirtied.
        os.utime(source_to_touch, ns=(original_atime, original_mtime))


def test_plugin_recovers_from_corrupt_cache_in_packages_mode(tmp_path: Path) -> None:
    """Phase 7 E6: a corrupted cache manifest triggers regeneration, not a hard failure.

    When the cached ``projection-manifest.json`` contains invalid JSON or fails
    Pydantic validation, ``_try_load_cached_manifest`` logs to stderr and returns
    None.  The plugin then runs full generation and writes a valid replacement.
    No ``CompileError`` should be raised.
    """
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.diamond_runtime",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)
    options.ignore_missing_imports = True

    # First init — generates valid cache.
    SageCategoryProjectionPlugin(options)
    manifest_path = cache_dir / "projection-manifest.json"
    assert manifest_path.is_file()

    # Corrupt the manifest with invalid JSON.
    manifest_path.write_text("{ this is not valid JSON !!!")

    # Second init — corrupt manifest detected → graceful regeneration → no CompileError.
    plugin_after_recovery = SageCategoryProjectionPlugin(options)

    # The manifest must now be a valid, loadable file again.
    recovered_manifest = load_manifest(manifest_path)
    assert recovered_manifest.projections, (
        "Recovered manifest must contain projections after regeneration from corrupt cache"
    )
    assert plugin_after_recovery._manifest.semantic_projection_digest == (
        recovered_manifest.semantic_projection_digest
    ), "Plugin's loaded manifest must match the regenerated manifest on disk"


def test_plugin_package_mode_preserves_existing_mypy_path(tmp_path: Path) -> None:
    cache_dir = tmp_path / "sage-category-cache"
    preexisting_path = tmp_path / "existing-mypy-path"
    preexisting_path.mkdir()
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.diamond_runtime",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)
    options.ignore_missing_imports = True
    options.mypy_path = [str(preexisting_path)]

    SageCategoryProjectionPlugin(options)

    assert options.mypy_path == [str(preexisting_path)]
    assert not (cache_dir / "stubs").exists()


def _build_fixture(
    config_path: Path,
    tmp_path: Path,
    *,
    fixture_path: Path = FIXTURE_PATH,
    fixture_module: str = FIXTURE_MODULE,
    fixture_sources: Sequence[tuple[Path, str]] | None = None,
    mypy_path_entries: Sequence[Path] = (REPO_ROOT,),
) -> BuildResult:
    sources = fixture_sources or ((fixture_path, fixture_module),)
    options = Options()
    options.config_file = str(config_path)
    options.plugins = ["sage_mypy_category_plugin.plugin"]
    options.incremental = False
    options.cache_dir = str(tmp_path / "mypy-cache")
    options.mypy_path = [str(path) for path in mypy_path_entries]
    options.ignore_missing_imports = True
    return build(
        sources=[
            BuildSource(str(source_path), source_module, None)
            for source_path, source_module in sources
        ],
        options=options,
    )


def _plugin_config_data(config_path: Path) -> dict[str, str]:
    options = Options()
    options.config_file = str(config_path)
    return SageCategoryProjectionPlugin(options).report_config_data(
        ctx=None,  # type: ignore[arg-type]
    )


def _build_fixture_without_plugin(
    tmp_path: Path,
    *,
    fixture_path: Path = FIXTURE_PATH,
    fixture_module: str = FIXTURE_MODULE,
    fixture_sources: Sequence[tuple[Path, str]] | None = None,
    mypy_path_entries: Sequence[Path] = (REPO_ROOT,),
) -> BuildResult:
    sources = fixture_sources or ((fixture_path, fixture_module),)
    options = Options()
    options.incremental = False
    options.cache_dir = str(tmp_path / "baseline-mypy-cache")
    options.mypy_path = [str(path) for path in mypy_path_entries]
    options.ignore_missing_imports = True
    return build(
        sources=[
            BuildSource(str(source_path), source_module, None)
            for source_path, source_module in sources
        ],
        options=options,
    )


def _nested_typeinfo(
    result: BuildResult,
    *,
    module: str,
    outer: str,
    inner: str,
) -> TypeInfo:
    outer_node = result.files[module].names[outer].node
    assert isinstance(outer_node, TypeInfo)

    inner_node = outer_node.names[inner].node
    assert isinstance(inner_node, TypeInfo)
    return inner_node


def _typeinfo_for_fullname(result: BuildResult, fullname: str) -> TypeInfo:
    parts = fullname.split(".")
    for split_index in range(len(parts), 0, -1):
        module_name = ".".join(parts[:split_index])
        module = result.files.get(module_name)
        if module is None:
            continue

        node: TypeInfo | None = None
        scope: TypeInfo | None = None
        for part in parts[split_index:]:
            names = module.names if scope is None else scope.names
            symbol = names.get(part)
            if symbol is None or not isinstance(symbol.node, TypeInfo):
                node = None
                break
            node = symbol.node
            scope = node
        else:
            if node is not None:
                return node

    raise AssertionError(f"Could not resolve TypeInfo for {fullname}")


def _inner_typeinfo(outer_info: TypeInfo, inner: str) -> TypeInfo:
    inner_node = outer_info.names[inner].node
    assert isinstance(inner_node, TypeInfo)
    return inner_node


def _contains_error_fragment(result: BuildResult, fragment: str) -> bool:
    return any(fragment in error for error in result.errors)

def _source_module_records_for_modules(
    stub_root: Path,
    module_names: tuple[str, ...],
) -> tuple[SourceModuleRecord, ...]:
    return tuple(
        SourceModuleRecord(
            module=module_name,
            path=str(stub_root.joinpath(*module_name.split(".")).with_suffix(".pyi")),
            sha256="0" * 64,
            mtime_ns=0,
        )
        for module_name in module_names
    )


def _write_empty_stub_module(stub_root: Path, module_name: str) -> SourceModuleRecord:
    path = stub_root.joinpath(*module_name.split(".")).with_suffix(".pyi")
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_stub_package_markers(stub_root, path.parent)
    path.write_text("")
    path_bytes = path.read_bytes()
    path_stat = path.stat()
    return SourceModuleRecord(
        module=module_name,
        path=str(path),
        sha256=sha256(path_bytes).hexdigest(),
        mtime_ns=path_stat.st_mtime_ns,
    )


def _write_stub_package_markers(stub_root: Path, package_dir: Path) -> None:
    current = package_dir
    packages: list[Path] = []
    while current != stub_root:
        packages.append(current)
        current = current.parent
    for package in reversed(packages):
        (package / "__init__.pyi").write_text("")


def _projected_source_module_names(
    projections: tuple[ProviderProjection, ...],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            _importable_module_name(fullname)
            for fullname in _projection_fullnames(projections)
            if not _is_intrinsic_fullname(fullname)
        )
    )


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


def _is_intrinsic_fullname(fullname: str) -> bool:
    return fullname == "builtins" or fullname.startswith("builtins.")


def _importable_module_name(fullname: str) -> str:
    parts = fullname.split(".")
    for split_index in range(len(parts), 0, -1):
        module_name = ".".join(parts[:split_index])
        try:
            import_module(module_name)
        except ModuleNotFoundError:
            continue
        return module_name
    raise AssertionError(f"Could not find importable module for {fullname!r}")

