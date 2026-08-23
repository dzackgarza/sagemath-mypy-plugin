"""Production lifecycle test: normal config via subprocess shellout.

This test proves the plugin works with the final production contract:
the Sage environment's Python plus plugin configuration, with upstream Sage provider
visibility supplied by the installed Sage-version sidecar stubs.  The config
does not predeclare ``cache_dir/stubs`` and does not point at a pre-generated
manifest.

Behavioral conjunction verified:
  plugin on  + valid code   → exit 0, no errors
  plugin on  + invalid code → exit nonzero, standard mypy error
  plugin off + valid code   → exit nonzero, no base method was found
  plugin off + invalid code → exit nonzero, no base method was found
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_CATEGORIES_ROOT = REPO_ROOT / "tests" / "real_categories"
FINITE_SMALL_GROUPS_VALID = REAL_CATEGORIES_ROOT / "finite_small_groups_valid.py"
FINITE_SMALL_GROUPS_INVALID = REAL_CATEGORIES_ROOT / "finite_small_groups_invalid.py"


def _run_sage_mypy(
    config_path: Path,
    target_file: Path,
    *,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    """Run mypy with the Python interpreter beside the selected Sage launcher."""
    sage_python = Path(os.environ["SAGE_BIN"]).parent / "python"
    return subprocess.run(
        [
            str(sage_python),
            "-m",
            "mypy",
            "--config-file",
            str(config_path),
            "--no-incremental",
            str(target_file),
        ],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )


def _write_plugin_config(tmp_path: Path) -> tuple[Path, Path]:
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            [
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.real_categories",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            ]
        )
    )
    return config_path, cache_dir


def _write_baseline_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "mypy-baseline.ini"
    config_path.write_text("[mypy]\n")
    return config_path


def test_production_lifecycle_behavior_matrix(tmp_path: Path) -> None:
    """Plain subprocess mypy obeys the plugin on/off × valid/invalid matrix.

    Plugin-on cases use the normal README config shape:
      [mypy]
      plugins = sage_mypy_category_plugin.plugin

      [sage-mypy-category-plugin]
      packages = tests.real_categories
      roles = parent
      cache_dir = <cache_dir>

    No generated-stub mypy_path and no Python-API path injection.
    """
    plugin_config_path, cache_dir = _write_plugin_config(tmp_path)
    baseline_config_path = _write_baseline_config(tmp_path)

    result = _run_sage_mypy(
        plugin_config_path,
        FINITE_SMALL_GROUPS_VALID,
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, (
        f"Expected exit 0 for valid code with plugin on.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "no base method was found" not in result.stdout, (
        "Plugin should project provider MRO so @override resolves correctly.\n"
        f"stdout:\n{result.stdout}"
    )
    # The production cache is manifest-only. Upstream Sage provider visibility
    # comes from the installed sidecar stubs, not generated cache stubs.
    assert (cache_dir / "projection-manifest.json").is_file(), (
        "Plugin should have generated projection-manifest.json in cache_dir"
    )
    assert not (cache_dir / "stubs").exists(), (
        "Production plugin path must not generate upstream Sage stubs"
    )

    result = _run_sage_mypy(
        plugin_config_path,
        FINITE_SMALL_GROUPS_INVALID,
        cwd=REPO_ROOT,
    )

    assert result.returncode != 0, (
        f"Expected nonzero exit for invalid code (@override on non-existent method).\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "no base method was found" in result.stdout, (
        "Plugin-on + @override on nonexistent method should produce standard mypy error.\n"
        f"stdout:\n{result.stdout}"
    )

    result = _run_sage_mypy(
        baseline_config_path,
        FINITE_SMALL_GROUPS_VALID,
        cwd=REPO_ROOT,
    )

    assert result.returncode != 0, (
        "Expected nonzero exit for valid code with plugin off; the fixture must "
        "prove mypy needs projected provider MRO.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "no base method was found" in result.stdout, (
        "Plugin-off + valid override should fail because mypy cannot see Sage "
        "provider inheritance.\n"
        f"stdout:\n{result.stdout}"
    )

    result = _run_sage_mypy(
        baseline_config_path,
        FINITE_SMALL_GROUPS_INVALID,
        cwd=REPO_ROOT,
    )

    assert result.returncode != 0, (
        "Expected nonzero exit for invalid code with plugin off.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "no base method was found" in result.stdout, (
        "Plugin-off + invalid override should fail before Sage provider "
        "inheritance is projected.\n"
        f"stdout:\n{result.stdout}"
    )
