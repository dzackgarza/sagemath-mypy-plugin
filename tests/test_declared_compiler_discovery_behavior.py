from __future__ import annotations

from pathlib import Path

from mypy.build import BuildResult, build
from mypy.modulefinder import BuildSource
from mypy.options import Options

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PACKAGE = "tests.fixtures.invariant_core.declared_compiler_discovery"
VALID_MODULE = f"{FIXTURE_PACKAGE}.valid"
INVALID_MODULE = f"{FIXTURE_PACKAGE}.invalid"


def test_declared_compiler_discovery_precedes_constructor_probes(
    tmp_path: Path,
) -> None:
    config_path = _write_plugin_config(tmp_path)

    valid_with_plugin = _run_mypy(VALID_MODULE, tmp_path, config_path)
    valid_without_plugin = _run_mypy(VALID_MODULE, tmp_path, None)
    invalid_with_plugin = _run_mypy(INVALID_MODULE, tmp_path, config_path)
    invalid_without_plugin = _run_mypy(INVALID_MODULE, tmp_path, None)

    assert not valid_with_plugin.errors
    assert valid_without_plugin.errors
    assert invalid_with_plugin.errors
    assert invalid_without_plugin.errors


def _write_plugin_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                f"packages = {FIXTURE_PACKAGE}",
                "roles = parent",
                f"cache_dir = {tmp_path / 'projection-cache'}",
                "",
            )
        )
    )
    return config_path


def _run_mypy(
    module: str,
    tmp_path: Path,
    config_path: Path | None,
) -> BuildResult:
    options = Options()
    options.incremental = False
    options.ignore_missing_imports = True
    options.mypy_path = [str(REPO_ROOT)]
    options.cache_dir = str(
        tmp_path / ("mypy-cache-plugin" if config_path is not None else "mypy-cache")
    )
    if config_path is not None:
        options.config_file = str(config_path)
        options.plugins = ["sage_mypy_category_plugin.plugin"]
    return build(
        sources=[BuildSource(str(_module_path(module)), module, None)],
        options=options,
    )


def _module_path(module: str) -> Path:
    return REPO_ROOT / f"{module.replace('.', '/')}.py"
