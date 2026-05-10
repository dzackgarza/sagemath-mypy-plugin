"""Mypy integration tests for the Sage category override plugin."""
from __future__ import annotations
import importlib
import shutil
import sys
import tempfile
from pathlib import Path
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_FIXTURES_PKG = _FIXTURES_DIR / "sage" / "categories" / "mypy_test_fixtures"
_CONFIG_FILE = Path(__file__).resolve().parent / "mypy_test.ini"
_CONFIGURED_CONFIG_FILE = Path(__file__).resolve().parent / "mypy_configured.ini"
_STRICT_CONFIG_FILE = Path(__file__).resolve().parent / "mypy_strict_no_representatives.ini"


def _drop_fixture_module(module_name: str) -> None:
    sys.modules.pop(module_name, None)


def _run(
    fixture_name: str,
    config_file: Path = _CONFIG_FILE,
) -> tuple[int, str]:
    from mypy import api
    path = str(_FIXTURES_PKG / f"{fixture_name}.py")
    mod_name = f"sage.categories.mypy_test_fixtures.{fixture_name}"
    try:
        importlib.import_module(mod_name)
    except Exception:
        pass
    stdout, _stderr, code = api.run([
        "--config-file", str(config_file),
        "--no-incremental",
        path,
    ])
    return code, stdout


def _run_path(path: str) -> tuple[int, str]:
    from mypy import api
    stdout, _stderr, code = api.run(["--config-file", str(_CONFIG_FILE), path])
    return code, stdout


# ---- Core tests ----

def test_valid_override():
    code, _ = _run("test_valid_override")
    assert code == 0


def test_invalid_override():
    code, stdout = _run("test_invalid_override")
    assert code != 0
    assert "no base method was found" in stdout


def test_diamond_override():
    code, _ = _run("test_diamond")
    assert code == 0


def test_element_methods_override():
    code, _ = _run("test_element_methods")
    assert code == 0


def test_morphism_methods_override():
    code, _ = _run("test_morphism_methods")
    assert code == 0


def test_signature_mismatch():
    code, _ = _run("test_signature_mismatch")
    assert code != 0


def test_parameterized_no_config():
    code, _ = _run("test_parameterized_no_config")
    assert code == 0


def test_green_contributor_category_valid_override_surface():
    code, stdout = _run("test_green_contributor_category_valid")
    assert code == 0, stdout


@pytest.mark.parametrize(
    "fixture_name",
    [
        "test_green_contributor_missing_override",
        "test_green_contributor_signature_override",
        "test_green_contributor_liskov_override",
    ],
)
def test_green_contributor_category_rejects_standard_override_errors(fixture_name):
    code, stdout = _run(fixture_name)
    assert code != 0, stdout


# ---- Acceptance criterion 9: incremental mode determinism ----

def test_incremental_determinism():
    """Plugin behavior is deterministic under mypy incremental mode.

    Run mypy on a valid-override fixture twice using the same cache dir.
    Both runs must produce identical results (same exit code, same output).
    """
    from mypy import api

    fixture_path = str(_FIXTURES_PKG / "test_valid_override.py")
    cache_dir = tempfile.mkdtemp(prefix="mypy_cache_det_")
    try:
        base_args = [
            "--config-file", str(_CONFIG_FILE),
            "--cache-dir", cache_dir,
        ]

        # Run 1: fresh cache
        stdout1, _stderr1, code1 = api.run(base_args + [fixture_path])
        # Run 2: incremental (reuse same cache)
        stdout2, _stderr2, code2 = api.run(base_args + [fixture_path])

        assert code1 == code2 == 0, (
            f"Codes differ: run1={code1}, run2={code2}"
        )
        assert stdout1 == stdout2, (
            f"Output differs between incremental runs.\n"
            f"Run 1:\n{stdout1}\nRun 2:\n{stdout2}"
        )
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)


# ---- Acceptance criterion 10: ancestor change reactivity ----

def test_ancestor_change_reactivity():
    """Removing/renaming ancestor method causes @override failures.

    Run mypy against the real Sage fixture package, rename the ancestor
    method in place, then run mypy again with the same cache directory.
    The second run must observe the stale override and fail.
    """
    from mypy import api

    module_name = "sage.categories.mypy_test_fixtures.test_renamed_ancestor"
    fixture_path = _FIXTURES_PKG / "test_renamed_ancestor.py"
    original = fixture_path.read_text()
    cache_dir = tempfile.mkdtemp(prefix="mypy_cache_react_")
    base_args = [
        "--config-file", str(_CONFIG_FILE),
        "--cache-dir", cache_dir,
    ]

    try:
        importlib.invalidate_caches()
        _drop_fixture_module(module_name)
        stdout1, _, code1 = api.run(base_args + [str(fixture_path)])
        assert code1 == 0, (
            f"Expected pass before rename, got code {code1}\n{stdout1}"
        )

        modified = original.replace(
            "def f_to_be_deleted(self) -> int:",
            "def f_renamed_away(self) -> int:",
            1,
        )
        assert modified != original
        fixture_path.write_text(modified)

        importlib.invalidate_caches()
        _drop_fixture_module(module_name)

        stdout2, _, code2 = api.run(base_args + [str(fixture_path)])
        assert code2 != 0, (
            f"Expected fail after rename, got code {code2}\n{stdout2}"
        )
    finally:
        fixture_path.write_text(original)
        importlib.invalidate_caches()
        _drop_fixture_module(module_name)
        shutil.rmtree(cache_dir, ignore_errors=True)


# ---- Placeholders for future work ----

def test_homset_override():
    code, stdout = _run("test_homset")
    assert code == 0, stdout


def test_parameterized_configured():
    code, stdout = _run("test_parameterized_configured", _CONFIGURED_CONFIG_FILE)
    assert code == 0, stdout


def test_parameterized_strict_without_config_reports_diagnostic():
    code, stdout = _run("test_parameterized_configured", _STRICT_CONFIG_FILE)
    assert code != 0, stdout
    assert "[sage-category-parameterized]" in stdout


def test_unresolved_strict_reports_diagnostic():
    code, stdout = _run("test_unresolved_strict", _STRICT_CONFIG_FILE)
    assert code != 0, stdout
    assert "[sage-category-unresolved]" in stdout


def test_base_unmapped_strict_reports_diagnostic():
    code, stdout = _run("test_base_unmapped_strict", _STRICT_CONFIG_FILE)
    assert code != 0, stdout
    assert "[sage-category-base-unmapped]" in stdout


def test_typeinfo_missing_strict_reports_diagnostic():
    code, stdout = _run("test_typeinfo_missing_strict", _STRICT_CONFIG_FILE)
    assert code != 0, stdout
    assert "[sage-category-typeinfo-missing]" in stdout
