from __future__ import annotations

from pathlib import Path

from mypy.build import BuildResult, build
from mypy.modulefinder import BuildSource
from mypy.options import Options

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "invariant_core"
VALID = "tests.fixtures.invariant_core.graph_mor_valid"
INVALID = "tests.fixtures.invariant_core.graph_mor_invalid"


def test_graph_generated_mor_provider_behavior_matrix(tmp_path: Path) -> None:
    config = tmp_path / "mypy.ini"
    config.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.graph_mor_runtime",
                "roles = element",
                f"cache_dir = {tmp_path / 'projection'}",
                "",
            )
        )
    )

    with_plugin = _run_mypy((VALID, INVALID), tmp_path, config=config, plugin=True)
    without_plugin = _run_mypy((VALID, INVALID), tmp_path, config=config, plugin=False)

    assert not _errors_for(with_plugin, VALID)
    assert any("[attr-defined]" in error for error in _errors_for(without_plugin, VALID))
    assert any("[attr-defined]" in error for error in _errors_for(with_plugin, INVALID))
    assert any("[attr-defined]" in error for error in _errors_for(without_plugin, INVALID))


def _run_mypy(
    modules: tuple[str, ...],
    tmp_path: Path,
    *,
    config: Path,
    plugin: bool,
) -> BuildResult:
    options = Options()
    options.incremental = False
    options.cache_dir = str(tmp_path / ("cache-plugin" if plugin else "cache-plain"))
    options.mypy_path = [str(REPO_ROOT)]
    options.ignore_missing_imports = True
    if plugin:
        options.config_file = str(config)
        options.plugins = ["sage_mypy_category_plugin.plugin"]
    return build(sources=[_source(module) for module in modules], options=options)


def _source(module: str) -> BuildSource:
    path = FIXTURE_ROOT / f"{module.rsplit('.', maxsplit=1)[-1]}.py"
    return BuildSource(str(path), module, None)


def _errors_for(result: BuildResult, module: str) -> tuple[str, ...]:
    filename = f"{module.rsplit('.', maxsplit=1)[-1]}.py"
    return tuple(error for error in result.errors if filename in error)


def test_live_mor_owner_projection_uses_generated_element_class() -> None:
    from sage_mypy_category_plugin.oracle import (
        provider_projections_for_runtime_element_classes,
    )
    from sage_mypy_category_plugin.resolver import (
        _runtime_element_classes_from_declaring_categories,
    )

    runtime_module = "tests.fixtures.invariant_core.graph_mor_runtime"
    runtime_classes = _runtime_element_classes_from_declaring_categories(
        (f"{runtime_module}.LiveGraphCategory",)
    )
    projections = provider_projections_for_runtime_element_classes(
        runtime_classes,
        provider_module_prefixes=(runtime_module,),
    )

    isometry = projections[f"{runtime_module}.IsometryArrowMethods"]
    assert isometry.provider_mro[:3] == (
        f"{runtime_module}.IsometryArrowMethods",
        f"{runtime_module}.EmbeddingArrowMethods",
        f"{runtime_module}.LinearArrowMethods",
    )
