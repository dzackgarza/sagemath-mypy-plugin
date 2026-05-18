from __future__ import annotations

from collections.abc import Sequence
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
    write_manifest,
)
from sage_mypy_category_plugin.oracle import provider_projections_for_categories
from sage_mypy_category_plugin.plugin import (
    CONFIG_SECTION,
    SageCategoryProjectionPlugin,
)
from sage_mypy_category_plugin.projection import ProviderProjection, ProviderRole

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
DIAMOND_SOURCE_MODULE = SourceModuleRecord(
    module=FIXTURE_MODULE,
    path="tests/fixtures/invariant_core/diamond_runtime.py",
    sha256="9f1f7a4a0d0b6dfd7f9d2d2c1d3b5e6a"
    "8b1c0f7a6d5e4c3b2a19080706050403",
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


@pytest.mark.parametrize(
    ("role", "provider_name"),
    (
        ("element", "ElementMethods"),
        ("subcategory", "SubcategoryMethods"),
        ("morphism", "MorphismMethods"),
    ),
)
def test_plugin_projects_non_parent_provider_role_typeinfo_mro(
    tmp_path: Path,
    role: ProviderRole,
    provider_name: str,
) -> None:
    projections = provider_projections_for_categories(
        PROVIDER_ROLES_FULLNAMES,
        roles=(role,),
    )
    provider = f"{PROVIDER_ROLES_MODULE}.BottomCategory.{provider_name}"
    expected_provider_mro = projections[provider].provider_mro
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
    )
    manifest_path = tmp_path / f"sage-category-{role}-projections.json"
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
        fixture_path=PROVIDER_ROLES_PATH,
        fixture_module=PROVIDER_ROLES_MODULE,
    )
    result_without_plugin = _build_fixture_without_plugin(
        tmp_path,
        fixture_path=PROVIDER_ROLES_PATH,
        fixture_module=PROVIDER_ROLES_MODULE,
    )
    role_info = _nested_typeinfo(
        result,
        module=PROVIDER_ROLES_MODULE,
        outer="BottomCategory",
        inner=provider_name,
    )
    baseline_role_info = _nested_typeinfo(
        result_without_plugin,
        module=PROVIDER_ROLES_MODULE,
        outer="BottomCategory",
        inner=provider_name,
    )

    assert result.errors == []
    assert result_without_plugin.errors == []
    assert tuple(info.fullname for info in baseline_role_info.mro) == (
        provider,
        "builtins.object",
    )
    assert tuple(info.fullname for info in role_info.mro) == (
        *expected_provider_mro,
        "builtins.object",
    )


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
        source_modules=(DIAMOND_SOURCE_MODULE,),
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
    assert config_data["manifest_source_module_digest"] == (
        manifest.source_module_digest
    )
    assert manifest.source_module_by_module == {FIXTURE_MODULE: DIAMOND_SOURCE_MODULE}


def test_plugin_fails_clearly_when_manifest_option_is_missing(tmp_path: Path) -> None:
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
        f"Missing manifest option in [{CONFIG_SECTION}] section of {config_path}"
    ]


def test_plugin_resolves_cross_module_provider_bases_via_additional_deps(
    tmp_path: Path,
) -> None:
    base_path = tmp_path / "base_provider.py"
    consumer_path = tmp_path / "consumer.py"
    base_path.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "",
                "class BaseCategory:",
                "    class ParentMethods:",
                "        def base_method(self) -> int:",
                "            return 1",
                "",
            )
        )
    )
    consumer_path.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "",
                "class ConsumerCategory:",
                "    class ParentMethods:",
                "        def consumer_method(self) -> int:",
                "            return 2",
                "",
            )
        )
    )

    consumer_provider = "consumer.ConsumerCategory.ParentMethods"
    base_provider = "base_provider.BaseCategory.ParentMethods"
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=(
            ProviderProjection(
                provider=base_provider,
                role="parent",
                runtime_class="base_provider.BaseCategory.parent_class",
                runtime_bases=("builtins.object",),
                runtime_mro=(
                    "base_provider.BaseCategory.parent_class",
                    "builtins.object",
                ),
                provider_bases=(),
                provider_mro=(base_provider,),
            ),
            ProviderProjection(
                provider=consumer_provider,
                role="parent",
                runtime_class="consumer.ConsumerCategory.parent_class",
                runtime_bases=("base_provider.BaseCategory.parent_class",),
                runtime_mro=(
                    "consumer.ConsumerCategory.parent_class",
                    "base_provider.BaseCategory.parent_class",
                    "builtins.object",
                ),
                provider_bases=(base_provider,),
                provider_mro=(consumer_provider, base_provider),
            ),
        ),
    )
    manifest_path = tmp_path / "cross-module-projections.json"
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

    result = _build_fixture(
        config_path,
        tmp_path,
        fixture_path=consumer_path,
        fixture_module="consumer",
        mypy_path_entries=(REPO_ROOT, tmp_path),
    )
    result_without_plugin = _build_fixture_without_plugin(
        tmp_path,
        fixture_path=consumer_path,
        fixture_module="consumer",
        mypy_path_entries=(REPO_ROOT, tmp_path),
    )
    consumer_info = _nested_typeinfo(
        result,
        module="consumer",
        outer="ConsumerCategory",
        inner="ParentMethods",
    )
    baseline_consumer_info = _nested_typeinfo(
        result_without_plugin,
        module="consumer",
        outer="ConsumerCategory",
        inner="ParentMethods",
    )

    assert result.errors == []
    assert result_without_plugin.errors == []
    assert "base_provider" in result.files
    assert "base_provider" not in result_without_plugin.files
    assert tuple(info.fullname for info in baseline_consumer_info.mro) == (
        consumer_provider,
        "builtins.object",
    )
    assert tuple(info.fullname for info in consumer_info.mro) == (
        consumer_provider,
        base_provider,
        "builtins.object",
    )


def test_plugin_projection_is_stable_across_repeated_builds(tmp_path: Path) -> None:
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
    manifest_path = tmp_path / "stable-projections.json"
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

    first_result = _build_fixture(config_path, tmp_path)
    second_result = _build_fixture(config_path, tmp_path)
    first_info = _nested_typeinfo(
        first_result,
        module=FIXTURE_MODULE,
        outer="BottomCategory",
        inner="ParentMethods",
    )
    second_info = _nested_typeinfo(
        second_result,
        module=FIXTURE_MODULE,
        outer="BottomCategory",
        inner="ParentMethods",
    )

    assert first_result.errors == []
    assert second_result.errors == []
    assert tuple(info.fullname for info in first_info.mro) == (
        *expected_provider_mro,
        "builtins.object",
    )
    assert tuple(info.fullname for info in second_info.mro) == (
        *expected_provider_mro,
        "builtins.object",
    )


def test_plugin_reports_manifest_drift_and_rebuilds_projection(
    tmp_path: Path,
) -> None:
    projections = provider_projections_for_categories(
        CATEGORY_FULLNAMES,
        roles=("parent",),
    )
    original_projection = projections[BOTTOM_PROVIDER]
    original_mro = original_projection.provider_mro
    drifted_mro = (
        original_mro[0],
        original_mro[2],
        original_mro[1],
        *original_mro[3:],
    )
    drifted_projection = original_projection.model_copy(
        update={"provider_mro": drifted_mro}
    )
    original_manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
    )
    drifted_manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(
            projection
            if projection.provider != BOTTOM_PROVIDER
            else drifted_projection
            for projection in projections.values()
        ),
    )
    manifest_path = tmp_path / "drifting-projections.json"
    config_path = tmp_path / "mypy.ini"
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

    write_manifest(manifest_path, original_manifest)
    first_config_data = _plugin_config_data(config_path)
    first_result = _build_fixture(config_path, tmp_path)
    first_info = _nested_typeinfo(
        first_result,
        module=FIXTURE_MODULE,
        outer="BottomCategory",
        inner="ParentMethods",
    )

    write_manifest(manifest_path, drifted_manifest)
    second_config_data = _plugin_config_data(config_path)
    second_result = _build_fixture(config_path, tmp_path)
    second_info = _nested_typeinfo(
        second_result,
        module=FIXTURE_MODULE,
        outer="BottomCategory",
        inner="ParentMethods",
    )

    assert original_manifest.semantic_projection_digest != (
        drifted_manifest.semantic_projection_digest
    )
    assert first_config_data["manifest_digest"] != second_config_data["manifest_digest"]
    assert first_config_data["manifest_semantic_projection_digest"] != (
        second_config_data["manifest_semantic_projection_digest"]
    )
    assert first_result.errors == []
    assert second_result.errors == []
    assert tuple(info.fullname for info in first_info.mro) == (
        *original_mro,
        "builtins.object",
    )
    assert tuple(info.fullname for info in second_info.mro) == (
        *drifted_mro,
        "builtins.object",
    )


def _build_fixture(
    config_path: Path,
    tmp_path: Path,
    *,
    fixture_path: Path = FIXTURE_PATH,
    fixture_module: str = FIXTURE_MODULE,
    mypy_path_entries: Sequence[Path] = (REPO_ROOT,),
) -> BuildResult:
    options = Options()
    options.config_file = str(config_path)
    options.plugins = ["sage_mypy_category_plugin.plugin"]
    options.incremental = False
    options.cache_dir = str(tmp_path / "mypy-cache")
    options.mypy_path = [str(path) for path in mypy_path_entries]
    options.ignore_missing_imports = True
    return build(
        sources=[BuildSource(str(fixture_path), fixture_module, None)],
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
    mypy_path_entries: Sequence[Path] = (REPO_ROOT,),
) -> BuildResult:
    options = Options()
    options.incremental = False
    options.cache_dir = str(tmp_path / "baseline-mypy-cache")
    options.mypy_path = [str(path) for path in mypy_path_entries]
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
