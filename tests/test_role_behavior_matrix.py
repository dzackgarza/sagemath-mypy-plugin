from __future__ import annotations

from pathlib import Path

from mypy.build import BuildResult, build
from mypy.modulefinder import BuildSource
from mypy.options import Options

from sage_mypy_category_plugin.manifest import ProjectionManifest, write_manifest
from sage_mypy_category_plugin.oracle import provider_projections_for_categories

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "invariant_core"

BASE_CATEGORY_FULLNAMES = (
    "tests.fixtures.invariant_core.provider_roles.diamond.TopCategory",
    "tests.fixtures.invariant_core.provider_roles.diamond.LeftCategory",
    "tests.fixtures.invariant_core.provider_roles.diamond.RightCategory",
    "tests.fixtures.invariant_core.provider_roles.diamond.BottomCategory",
)

ROLE_BEHAVIOR_CASES = {
    "element_valid": (
        "tests.fixtures.invariant_core.role_behavior_element_valid",
        "tests.fixtures.invariant_core.role_behavior_element_valid.ValidElementOverrideCategory",
    ),
    "element_invalid": (
        "tests.fixtures.invariant_core.role_behavior_element_invalid",
        "tests.fixtures.invariant_core.role_behavior_element_invalid.InvalidElementOverrideCategory",
    ),
    "subcategory_valid": (
        "tests.fixtures.invariant_core.role_behavior_subcategory_valid",
        "tests.fixtures.invariant_core.role_behavior_subcategory_valid.ValidSubcategoryOverrideCategory",
    ),
    "subcategory_invalid": (
        "tests.fixtures.invariant_core.role_behavior_subcategory_invalid",
        "tests.fixtures.invariant_core.role_behavior_subcategory_invalid.InvalidSubcategoryOverrideCategory",
    ),
    "morphism_valid": (
        "tests.fixtures.invariant_core.role_behavior_morphism_valid",
        "tests.fixtures.invariant_core.role_behavior_morphism_valid.ValidMorphismOverrideCategory",
    ),
    "morphism_invalid": (
        "tests.fixtures.invariant_core.role_behavior_morphism_invalid",
        "tests.fixtures.invariant_core.role_behavior_morphism_invalid.InvalidMorphismOverrideCategory",
    ),
}

ROLE_GROUPS = {
    "element": (
        "element_valid",
        "element_invalid",
    ),
    "subcategory": (
        "subcategory_valid",
        "subcategory_invalid",
    ),
    "morphism": (
        "morphism_valid",
        "morphism_invalid",
    ),
}


def test_non_parent_role_behavior_matrix_uses_standard_mypy_inheritance_rules(
    tmp_path: Path,
) -> None:
    config_path = _write_plugin_config(tmp_path)

    with_plugin = _run_mypy(
        tuple(case[0] for case in ROLE_BEHAVIOR_CASES.values()),
        config_path,
        tmp_path,
    )
    without_plugin = _run_mypy_without_plugin(
        tuple(case[0] for case in ROLE_BEHAVIOR_CASES.values()),
        tmp_path,
    )

    assert not _case_errors(with_plugin, "element_valid")
    assert _case_contains(without_plugin, "element_valid", "no base method was found")
    assert _case_contains(with_plugin, "element_invalid", "no base method was found")
    assert _case_contains(without_plugin, "element_invalid", "no base method was found")

    assert not _case_errors(with_plugin, "subcategory_valid")
    assert _case_contains(without_plugin, "subcategory_valid", "no base method was found")
    assert _case_contains(with_plugin, "subcategory_invalid", "no base method was found")
    assert _case_contains(without_plugin, "subcategory_invalid", "no base method was found")

    assert not _case_errors(with_plugin, "morphism_valid")
    assert _case_contains(without_plugin, "morphism_valid", "no base method was found")
    assert _case_contains(with_plugin, "morphism_invalid", "no base method was found")
    assert _case_contains(without_plugin, "morphism_invalid", "no base method was found")


def _write_plugin_config(tmp_path: Path) -> Path:
    projected_providers = {}
    for role, case_names in ROLE_GROUPS.items():
        category_fullnames = list(BASE_CATEGORY_FULLNAMES)
        category_fullnames.extend(ROLE_BEHAVIOR_CASES[case_name][1] for case_name in case_names)
        projected_providers.update(
            provider_projections_for_categories(category_fullnames, roles=(role,))
        )
    projections = projected_providers
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
    return config_path


def _run_mypy(
    modules: tuple[str, ...],
    config_path: Path,
    tmp_path: Path,
) -> BuildResult:
    options = _options(tmp_path)
    options.config_file = str(config_path)
    options.plugins = ["sage_mypy_category_plugin.plugin"]
    return build(sources=[_source(module) for module in modules], options=options)


def _run_mypy_without_plugin(modules: tuple[str, ...], tmp_path: Path) -> BuildResult:
    return build(sources=[_source(module) for module in modules], options=_options(tmp_path))


def _options(tmp_path: Path) -> Options:
    options = Options()
    options.incremental = False
    options.cache_dir = str(tmp_path / "mypy-cache")
    options.mypy_path = [str(REPO_ROOT)]
    options.ignore_missing_imports = True
    return options


def _source(module: str) -> BuildSource:
    return BuildSource(str(_module_path(module)), module, None)


def _module_path(module: str) -> Path:
    filename = module.rsplit(".", maxsplit=1)[-1] + ".py"
    return FIXTURE_ROOT / filename


def _case_contains(result: BuildResult, case_name: str, fragment: str) -> bool:
    return any(fragment in error for error in _case_errors(result, case_name))


def _case_errors(result: BuildResult, case_name: str) -> tuple[str, ...]:
    filename = _module_path(ROLE_BEHAVIOR_CASES[case_name][0]).name
    return tuple(error for error in result.errors if filename in error)
