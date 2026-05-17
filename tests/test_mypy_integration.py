"""Mypy integration tests for the Sage category override plugin."""
from __future__ import annotations

from functools import cache
import importlib
import os
import subprocess
import shutil
import sys
import tempfile
from pathlib import Path
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_SAGE_FIXTURES_PKG = _FIXTURES_DIR / "sage" / "categories" / "mypy_test_fixtures"
_THIRD_PARTY_FIXTURES_PKG = (
    _FIXTURES_DIR / "third_party_pkg" / "categories" / "mypy_test_fixtures"
)
_CONFIG_FILE = Path(__file__).resolve().parent / "mypy_test.ini"
_CONFIGURED_CONFIG_FILE = Path(__file__).resolve().parent / "mypy_configured.ini"
_STRICT_CONFIG_FILE = Path(__file__).resolve().parent / "mypy_strict_no_representatives.ini"
_RESEARCH_ROOT = Path("/home/dzack/research")
_RESEARCH_MYPY_CONFIG = Path("/home/dzack/ai/quality-control/mypy-global.ini")
_MUTABLE_FIXTURE_NAMES = frozenset({"test_renamed_ancestor"})
_FATAL_MYPY_MARKERS = (
    "INTERNAL ERROR",
    "Traceback",
    "Segmentation fault",
    "Unhandled SIGSEGV",
)


def _drop_fixture_module(module_name: str) -> None:
    sys.modules.pop(module_name, None)


def _import_fixture(module_prefix: str, fixture_name: str) -> None:
    _drop_fixture_module(f"{module_prefix}.{fixture_name}")
    try:
        importlib.import_module(f"{module_prefix}.{fixture_name}")
    except Exception:
        pass


def _fixture_paths(fixture_dir: Path) -> tuple[Path, ...]:
    return tuple(
        path for path in sorted(fixture_dir.glob("test_*.py"))
        if path.stem not in _MUTABLE_FIXTURE_NAMES
    )


def _diagnostics_for_path(stdout: str, path: Path) -> str:
    rel_path = path.relative_to(_PROJECT_ROOT)
    prefixes = (f"{path}:", f"{rel_path}:")
    lines = [line for line in stdout.splitlines() if line.startswith(prefixes)]
    return "\n".join(lines)


def _assert_mypy_completed(stdout: str, code: int) -> None:
    if any(marker in stdout for marker in _FATAL_MYPY_MARKERS):
        raise AssertionError(stdout)
    if code not in (0, 1):
        raise AssertionError(stdout)


def _run_single_fixture(
    fixture_dir: Path,
    module_prefix: str,
    fixture_name: str,
    config_file: Path,
) -> tuple[int, str]:
    from mypy import api

    path = fixture_dir / f"{fixture_name}.py"
    _import_fixture(module_prefix, fixture_name)
    stdout, _stderr, code = api.run([
        "--config-file", str(config_file),
        "--no-incremental",
        str(path),
    ])
    _assert_mypy_completed(stdout, code)
    return code, stdout


@cache
def _run_fixture_set(
    fixture_dir: Path,
    module_prefix: str,
    config_file: Path,
) -> str:
    from mypy import api

    paths = _fixture_paths(fixture_dir)
    for path in paths:
        _import_fixture(module_prefix, path.stem)
    stdout, _stderr, code = api.run([
        "--config-file", str(config_file),
        "--no-incremental",
        *(str(path) for path in paths),
    ])
    _assert_mypy_completed(stdout, code)
    return stdout


def _run_fixture(
    fixture_dir: Path,
    module_prefix: str,
    fixture_name: str,
    config_file: Path = _CONFIG_FILE,
) -> tuple[int, str]:
    if fixture_name in _MUTABLE_FIXTURE_NAMES:
        return _run_single_fixture(
            fixture_dir,
            module_prefix,
            fixture_name,
            config_file,
        )
    path = fixture_dir / f"{fixture_name}.py"
    diagnostics = _diagnostics_for_path(
        _run_fixture_set(fixture_dir, module_prefix, config_file),
        path,
    )
    return (1 if diagnostics else 0), diagnostics


def _run(
    fixture_name: str,
    config_file: Path = _CONFIG_FILE,
) -> tuple[int, str]:
    return _run_fixture(
        _SAGE_FIXTURES_PKG,
        "sage.categories.mypy_test_fixtures",
        fixture_name,
        config_file,
    )


def _run_third_party(
    fixture_name: str,
    config_file: Path = _CONFIG_FILE,
) -> tuple[int, str]:
    return _run_fixture(
        _THIRD_PARTY_FIXTURES_PKG,
        "third_party_pkg.categories.mypy_test_fixtures",
        fixture_name,
        config_file,
    )


def _run_path(path: str) -> tuple[int, str]:
    from mypy import api
    stdout, _stderr, code = api.run(["--config-file", str(_CONFIG_FILE), path])
    return code, stdout


def _projection_summary(
    fullname: str,
    representatives: dict[str, tuple[str, ...]] | None = None,
) -> str:
    from sage_mypy_category_plugin.introspection import method_container_projection

    projection = method_container_projection(fullname, representatives)
    assert projection is not None
    return (
        f"source={projection.source_fullname}\n"
        f"dynamic_class={projection.dynamic_class}\n"
        f"dynamic_bases={projection.dynamic_bases}\n"
        f"static_bases={projection.static_bases}\n"
        f"unmapped_dynamic_bases={projection.unmapped_dynamic_bases}"
    )


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


def test_third_party_final_method_override_rejected():
    code, stdout = _run_third_party("test_final_method_override")
    assert code != 0, stdout
    assert "Cannot override final attribute" in stdout


def test_third_party_final_classmethod_override_rejected():
    code, stdout = _run_third_party("test_final_classmethod_override")
    assert code != 0, stdout
    assert "Cannot override final attribute" in stdout


def test_third_party_final_attribute_override_rejected():
    code, stdout = _run_third_party("test_final_attribute_override")
    assert code != 0, stdout
    assert (
        "Cannot override final attribute" in stdout
        or "Cannot assign to final name" in stdout
    ), stdout


def test_third_party_final_signature_override_rejected():
    code, stdout = _run_third_party("test_final_signature_override")
    assert code != 0, stdout
    assert "Cannot override final attribute" in stdout
    assert "Signature of \"Of\" incompatible with supertype" in stdout


def test_incremental_determinism():
    """Plugin behavior is deterministic under mypy incremental mode.

    Run mypy on a valid-override fixture twice using the same cache dir.
    Both runs must produce identical results (same exit code, same output).
    """
    from mypy import api

    fixture_path = str(_SAGE_FIXTURES_PKG / "test_valid_override.py")
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
    fixture_path = _SAGE_FIXTURES_PKG / "test_renamed_ancestor.py"
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


def test_research_homsets_run_does_not_segfault():
    if not _RESEARCH_ROOT.exists():
        pytest.skip("local research checkout not available")
    if not _RESEARCH_MYPY_CONFIG.exists():
        pytest.skip("local research mypy config not available")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(_PROJECT_ROOT)
    result = subprocess.run(
        [
            "mypy",
            "--config-file",
            str(_RESEARCH_MYPY_CONFIG),
            "category_specs/homsets/homsets.py",
            "category_specs/homsets/endsets.py",
            "category_specs/homsets/autsets.py",
            "category_specs/sets/homsets.py",
            "category_specs/topological_spaces/homsets.py",
        ],
        cwd=_RESEARCH_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    combined_output = result.stdout + result.stderr

    assert result.returncode != 139, combined_output
    assert "INTERNAL ERROR" not in combined_output
    assert "Unhandled SIGSEGV" not in combined_output, combined_output
    assert "Segmentation fault" not in combined_output, combined_output


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
