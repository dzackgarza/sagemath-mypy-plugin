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
    "tests.fixtures.invariant_core.diamond_runtime.TopCategory",
    "tests.fixtures.invariant_core.diamond_runtime.LeftCategory",
    "tests.fixtures.invariant_core.diamond_runtime.RightCategory",
    "tests.fixtures.invariant_core.diamond_runtime.BottomCategory",
)
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


def _write_plugin_config(tmp_path: Path) -> Path:
    category_fullnames = list(BASE_CATEGORY_FULLNAMES)
    for case in BEHAVIOR_CASES.values():
        category_fullnames.extend(case[1:])
    projections = provider_projections_for_categories(category_fullnames, roles=("parent",))
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
    options.enable_error_code = ["explicit-override"]
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
    filename = _module_path(BEHAVIOR_CASES[case_name][0]).name
    return tuple(error for error in result.errors if filename in error)
