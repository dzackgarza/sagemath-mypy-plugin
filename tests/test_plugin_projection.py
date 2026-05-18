from __future__ import annotations

from pathlib import Path

import pytest
from mypy.build import BuildResult, build
from mypy.modulefinder import BuildSource
from mypy.nodes import TypeInfo
from mypy.options import Options

from sage_mypy_category_plugin.manifest import ProjectionManifest, write_manifest
from sage_mypy_category_plugin.oracle import provider_projections_for_categories
from sage_mypy_category_plugin.plugin import SageCategoryProjectionPlugin
from sage_mypy_category_plugin.projection import ProviderProjection

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


def test_plugin_projects_typeinfo_mro_from_manifest(tmp_path: Path) -> None:
    projections = provider_projections_for_categories(
        CATEGORY_FULLNAMES,
        roles=("parent",),
    )
    expected_provider_mro = projections[BOTTOM_PROVIDER].provider_mro
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
    )
    manifest_path = tmp_path / "sage-category-projections.json"
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

    result = _build_fixture(config_path, tmp_path)
    result_without_plugin = _build_fixture_without_plugin(tmp_path)
    bottom_parent_info = _nested_typeinfo(
        result,
        module=FIXTURE_MODULE,
        outer="BottomCategory",
        inner="ParentMethods",
    )
    baseline_bottom_parent_info = _nested_typeinfo(
        result_without_plugin,
        module=FIXTURE_MODULE,
        outer="BottomCategory",
        inner="ParentMethods",
    )

    assert result.errors == []
    assert result_without_plugin.errors == []
    assert tuple(info.fullname for info in baseline_bottom_parent_info.mro) == (
        BOTTOM_PROVIDER,
        "builtins.object",
    )
    assert tuple(info.fullname for info in bottom_parent_info.mro) == (
        *expected_provider_mro,
        "builtins.object",
    )


def test_plugin_projects_category_specs_like_alias_typeinfo_mro(
    tmp_path: Path,
) -> None:
    projections = provider_projections_for_categories(
        CATEGORY_SPECS_LIKE_FULLNAMES,
        roles=("parent",),
    )
    expected_provider_mro = projections[
        CATEGORY_SPECS_LIKE_COMMUTATIVE_PROVIDER
    ].provider_mro
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
    )
    manifest_path = tmp_path / "sage-category-specs-like-projections.json"
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

    result = _build_fixture(
        config_path,
        tmp_path,
        fixture_path=CATEGORY_SPECS_LIKE_SUBCATEGORY_PATH,
        fixture_module=CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE,
    )
    result_without_plugin = _build_fixture_without_plugin(
        tmp_path,
        fixture_path=CATEGORY_SPECS_LIKE_SUBCATEGORY_PATH,
        fixture_module=CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE,
    )
    commutative_parent_info = _nested_typeinfo(
        result,
        module=CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE,
        outer="_CommutativeRings",
        inner="ParentMethods",
    )
    baseline_commutative_parent_info = _nested_typeinfo(
        result_without_plugin,
        module=CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE,
        outer="_CommutativeRings",
        inner="ParentMethods",
    )
    root_parent_info = result.files[CATEGORY_SPECS_LIKE_ROOT_MODULE].names[
        "_RingObjectMethods"
    ].node

    assert isinstance(root_parent_info, TypeInfo)
    assert result.errors == []
    assert result_without_plugin.errors == []
    assert tuple(info.fullname for info in baseline_commutative_parent_info.mro) == (
        CATEGORY_SPECS_LIKE_COMMUTATIVE_PROVIDER,
        "builtins.object",
    )
    assert tuple(info.fullname for info in commutative_parent_info.mro) == (
        *expected_provider_mro,
        "builtins.object",
    )
    assert expected_provider_mro == (
        CATEGORY_SPECS_LIKE_COMMUTATIVE_PROVIDER,
        CATEGORY_SPECS_LIKE_ROOT_PROVIDER,
    )
    assert root_parent_info.fullname == CATEGORY_SPECS_LIKE_ROOT_PROVIDER


@pytest.mark.parametrize("field", ("provider_bases", "provider_mro"))
def test_plugin_fails_strict_projection_for_mutated_field(
    tmp_path: Path, field: str
) -> None:
    projections = provider_projections_for_categories(
        CATEGORY_FULLNAMES,
        roles=("parent",),
    )
    missing_provider = f"{FIXTURE_MODULE}.MissingParentMethods"
    missing_projection = ProviderProjection(
        provider=missing_provider,
        role="parent",
        runtime_class="tests.fixtures.invariant_core.missing.MissingParentMethods",
        runtime_bases=(),
        runtime_mro=(),
        provider_bases=(),
        provider_mro=(missing_provider,),
    )

    mutated_projection = projections[BOTTOM_PROVIDER]
    if field == "provider_bases":
        mutated_projection = mutated_projection.model_copy(
            update={
                "provider_bases": (
                    *mutated_projection.provider_bases,
                    missing_provider,
                )
            }
        )
    else:
        mutated_projection = mutated_projection.model_copy(
            update={"provider_mro": (*mutated_projection.provider_mro, missing_provider)}
        )

    manifest_projections = tuple(
        projection
        if projection.provider != BOTTOM_PROVIDER
        else mutated_projection
        for projection in projections.values()
    )
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=(*manifest_projections, missing_projection),
    )
    manifest_path = tmp_path / "sage-category-projections-missing.json"
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

    result = _build_fixture(config_path, tmp_path)
    result_without_plugin = _build_fixture_without_plugin(tmp_path)

    strict_projection = _nested_typeinfo(
        result,
        module=FIXTURE_MODULE,
        outer="BottomCategory",
        inner="ParentMethods",
    )
    baseline_projection = _nested_typeinfo(
        result_without_plugin,
        module=FIXTURE_MODULE,
        outer="BottomCategory",
        inner="ParentMethods",
    )

    assert result_without_plugin.errors == []
    assert (
        tuple(info.fullname for info in strict_projection.mro)
        == tuple(info.fullname for info in baseline_projection.mro)
    )

    assert any("missing symbols" in error for error in result.errors)


def test_plugin_reports_semantic_manifest_config_data(tmp_path: Path) -> None:
    projections = provider_projections_for_categories(
        CATEGORY_FULLNAMES,
        roles=("parent",),
    )
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
    )
    manifest_path = tmp_path / "sage-category-projections.json"
    config_path = tmp_path / "mypy.ini"
    write_manifest(manifest_path, manifest)
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )

    options = Options()
    options.config_file = str(config_path)
    config_data = SageCategoryProjectionPlugin(options).report_config_data(
        ctx=None,  # type: ignore[arg-type]
    )

    assert config_data["manifest_semantic_projection_digest"] == (
        manifest.semantic_projection_digest
    )
    assert config_data["manifest_plugin_schema_version"] == (
        manifest.plugin_schema_version
    )
    assert config_data["manifest_mypy_min_version"] == manifest.mypy_min_version
    assert config_data["manifest_mypy_max_version"] == manifest.mypy_max_version


def _build_fixture(
    config_path: Path,
    tmp_path: Path,
    *,
    fixture_path: Path = FIXTURE_PATH,
    fixture_module: str = FIXTURE_MODULE,
) -> BuildResult:
    options = Options()
    options.config_file = str(config_path)
    options.plugins = ["sage_mypy_category_plugin.plugin"]
    options.incremental = False
    options.cache_dir = str(tmp_path / "mypy-cache")
    options.mypy_path = [str(REPO_ROOT)]
    options.ignore_missing_imports = True
    return build(
        sources=[BuildSource(str(fixture_path), fixture_module, None)],
        options=options,
    )


def _build_fixture_without_plugin(
    tmp_path: Path,
    *,
    fixture_path: Path = FIXTURE_PATH,
    fixture_module: str = FIXTURE_MODULE,
) -> BuildResult:
    options = Options()
    options.incremental = False
    options.cache_dir = str(tmp_path / "baseline-mypy-cache")
    options.mypy_path = [str(REPO_ROOT)]
    options.ignore_missing_imports = True
    return build(
        sources=[BuildSource(str(fixture_path), fixture_module, None)],
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
