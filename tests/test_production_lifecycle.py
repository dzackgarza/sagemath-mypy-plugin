"""Production lifecycle test: normal config via subprocess shellout.

This test proves the plugin works with the final production contract:
``sage -python -m mypy`` plus plugin configuration, with upstream Sage provider
visibility supplied by the installed Sage-version sidecar stubs.  The config
does not predeclare ``cache_dir/stubs`` and does not point at a pre-generated
manifest.

Behavioral conjunction verified:
  plugin on  + valid code   → exit 0, no errors
  plugin on  + invalid code → exit nonzero, standard mypy error
"""
from __future__ import annotations

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
    """Shell out to ``sage -python -m mypy`` exactly as the README prescribes."""
    return subprocess.run(
        [
            "sage",
            "-python",
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


def test_production_lifecycle_valid_code_exits_clean(tmp_path: Path) -> None:
    """Plugin-on + valid code → exit 0 with no errors via subprocess shellout.

    Uses the normal config shape documented in README.md:
      [mypy]
      plugins = sage_mypy_category_plugin.plugin

      [sage-mypy-category-plugin]
      packages = tests.real_categories
      roles = parent
      cache_dir = <cache_dir>

    No generated-stub mypy_path and no Python-API path injection.
    """
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

    result = _run_sage_mypy(
        config_path,
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


def test_production_lifecycle_invalid_code_exits_nonzero(tmp_path: Path) -> None:
    """Plugin-on + invalid code → exit nonzero with standard mypy error via shellout.

    Same config as the valid-code test.  A @override on a non-existent method
    should still produce a standard mypy error even though the plugin is active.
    """
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

    result = _run_sage_mypy(
        config_path,
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
