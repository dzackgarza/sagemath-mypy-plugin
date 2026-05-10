"""Mypy integration tests for the Sage category override plugin.

Each test invokes mypy (via ``sage -python -m mypy``) on a fixture file
that defines artificial Sage Category subclasses with method containers
annotated with ``@typing.override``.

Run via::

    sage -c "import pytest; pytest.main(['tests/test_mypy_integration.py', '-v', '--tb=short'])"

Not ``pytest tests/test_mypy_integration.py -v`` — we need Sage's Python.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_FIXTURES_PKG = _FIXTURES_DIR / "sage" / "categories" / "mypy_test_fixtures"
_CONFIG_FILE = Path(__file__).resolve().parent / "mypy_test.ini"

# Ensure they exist before we try to use them.
assert _PROJECT_ROOT.is_dir(), f"Project root missing: {_PROJECT_ROOT}"
assert _FIXTURES_PKG.is_dir(), f"Fixtures package missing: {_FIXTURES_PKG}"
assert _CONFIG_FILE.is_file(), f"Mypy config missing: {_CONFIG_FILE}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_mypy_on_fixture(
    fixture_name: str,
    *,
    extra_args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run mypy on a single fixture file under the fixtures package.

    Args:
        fixture_name: The module name *within* the fixtures package, e.g.
            ``"test_valid_override"`` (will be resolved to the .py file).
        extra_args: Additional mypy arguments.
        env: Environment variables merged on top of os.environ.

    Returns:
        (exit_code, stdout, stderr)
    """
    fixture_file = _FIXTURES_PKG / f"{fixture_name}.py"
    if not fixture_file.is_file():
        raise FileNotFoundError(f"Fixture not found: {fixture_file}")

    cmd = [
        "sage",
        "-python",
        "-m",
        "mypy",
        "--config-file",
        str(_CONFIG_FILE),
        str(fixture_file),
    ]
    if extra_args:
        cmd.extend(extra_args)

    # Build the PYTHONPATH for the subprocess so both the plugin and the
    # fixtures are importable.
    run_env = dict(os.environ)
    pythonpath_parts = [
        str(_PROJECT_ROOT),          # for ``sage_mypy_category_plugin``
        str(_FIXTURES_DIR),          # for ``sage.categories.mypy_test_fixtures``
    ]
    existing_path = run_env.get("PYTHONPATH", "")
    if existing_path:
        pythonpath_parts.insert(0, existing_path)
    run_env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    if env:
        run_env.update(env)

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=run_env,
        cwd=str(_PROJECT_ROOT),
    )

    return proc.returncode, proc.stdout, proc.stderr


def _fresh_cache_dir() -> str:
    """Create a temporary directory to hold an isolated mypy cache."""
    return tempfile.mkdtemp(prefix="mypy_test_cache_")


def _fixture_module_path(name: str) -> Path:
    return _FIXTURES_PKG / f"{name}.py"


# ---------------------------------------------------------------------------
# Test: valid override
# ---------------------------------------------------------------------------


def test_valid_override():
    """_B.ParentMethods.@override f → PASS (f exists in _A.ParentMethods)."""
    exit_code, stdout, stderr = run_mypy_on_fixture("test_valid_override")
    assert exit_code == 0, (
        f"Expected exit 0, got {exit_code}\n"
        f"stdout:\n{stdout}\n"
        f"stderr:\n{stderr}"
    )


# ---------------------------------------------------------------------------
# Test: invalid override
# ---------------------------------------------------------------------------


def test_invalid_override():
    """_B2.ParentMethods.@override g → FAIL (g absent from all ancestors)."""
    exit_code, stdout, stderr = run_mypy_on_fixture("test_invalid_override")

    # mypy should report the override error.
    # Even with ``# type: ignore[misc]`` in the source, mypy's own @override
    # check may still emit an error that escapes the inline ignore — that's
    # fine; the fixture comment only marks *intent*.
    assert exit_code != 0, (
        f"Expected non-zero exit for invalid @override, got {exit_code}\n"
        f"stderr:\n{stderr}"
    )
    assert (
        "no base method was found" in stderr or "override" in stderr.lower()
    ), f"Expected override-related error in stderr, got:\n{stderr}"


# ---------------------------------------------------------------------------
# Test: diamond hierarchy
# ---------------------------------------------------------------------------


def test_diamond_override():
    """D3.ParentMethods.@override f → PASS (f in both B3 and C3)."""
    exit_code, stdout, stderr = run_mypy_on_fixture("test_diamond")
    assert exit_code == 0, (
        f"Expected exit 0 for diamond override, got {exit_code}\n"
        f"stderr:\n{stderr}"
    )


# ---------------------------------------------------------------------------
# Test: ElementMethods override
# ---------------------------------------------------------------------------


def test_element_methods_override():
    """B4.ElementMethods.@override e → PASS (e in A4.ElementMethods)."""
    exit_code, stdout, stderr = run_mypy_on_fixture("test_element_methods")
    assert exit_code == 0, (
        f"Expected exit 0 for ElementMethods override, got {exit_code}\n"
        f"stderr:\n{stderr}"
    )


# ---------------------------------------------------------------------------
# Test: MorphismMethods override
# ---------------------------------------------------------------------------


def test_morphism_methods_override():
    """B5.MorphismMethods.@override m → PASS (m in A5.MorphismMethods)."""
    exit_code, stdout, stderr = run_mypy_on_fixture("test_morphism_methods")
    assert exit_code == 0, (
        f"Expected exit 0 for MorphismMethods override, got {exit_code}\n"
        f"stderr:\n{stderr}"
    )


# ---------------------------------------------------------------------------
# Test: Homsets override
# ---------------------------------------------------------------------------


def test_homset_override():
    """B6.Homsets.ParentMethods.@override f → PASS (f in A6.Homsets.ParentMethods)."""
    exit_code, stdout, stderr = run_mypy_on_fixture("test_homset")
    assert exit_code == 0, (
        f"Expected exit 0 for Homsets override, got {exit_code}\n"
        f"stderr:\n{stderr}"
    )


# ---------------------------------------------------------------------------
# Test: parameterized category (no config)
# ---------------------------------------------------------------------------


def test_parameterized_no_config():
    """Parameterized category with no @override → plugin shouldn't crash, exit 0."""
    exit_code, stdout, stderr = run_mypy_on_fixture("test_parameterized_no_config")
    assert exit_code == 0, (
        f"Expected exit 0 for parameterized category, got {exit_code}\n"
        f"stderr:\n{stderr}"
    )


# ---------------------------------------------------------------------------
# Test: parameterized category (configured)
# ---------------------------------------------------------------------------


def test_parameterized_configured():
    """Parameterized category with basic instantiation — mypy exit 0."""
    exit_code, stdout, stderr = run_mypy_on_fixture("test_parameterized_configured")
    assert exit_code == 0, (
        f"Expected exit 0 for parameterized configured, got {exit_code}\n"
        f"stderr:\n{stderr}"
    )


# ---------------------------------------------------------------------------
# Test: signature mismatch
# ---------------------------------------------------------------------------


def test_signature_mismatch():
    """B9.ParentMethods.@override f(x: str) → FAIL (x: int in ancestor)."""
    exit_code, stdout, stderr = run_mypy_on_fixture("test_signature_mismatch")
    assert exit_code != 0, (
        f"Expected non-zero exit for signature mismatch, got {exit_code}\n"
        f"stdout:\n{stdout}\nstderr:\n{stderr}"
    )


# ---------------------------------------------------------------------------
# Test: renamed ancestor
# ---------------------------------------------------------------------------


def test_renamed_ancestor():
    """Copy valid override fixture, remove ancestor method, verify mypy fails."""
    # Work in a temp copy so we don't mangle the original fixture.
    tmp_dir = tempfile.mkdtemp(prefix="mypy_renamed_")
    try:
        src = _fixture_module_path("test_renamed_ancestor")
        dst = os.path.join(tmp_dir, "test_renamed_ancestor.py")
        shutil.copy2(str(src), dst)

        # Run on the copy (should pass — ancestor method exists).
        exit_code, _, stderr = _run_mypy_on_path(dst)
        assert exit_code == 0, (
            f"Expected exit 0 before renaming ancestor, got {exit_code}\n"
            f"stderr:\n{stderr}"
        )

        # Remove the ancestor method (rename it).
        with open(dst, "r") as fh:
            content = fh.read()
        modified = content.replace("def f_to_be_deleted", "def f_renamed_away")
        with open(dst, "w") as fh:
            fh.write(modified)

        # Run again — should now fail because the ancestor method is gone.
        exit_code2, _, stderr2 = _run_mypy_on_path(dst)
        assert exit_code2 != 0, (
            f"Expected non-zero exit after renaming ancestor, got {exit_code2}\n"
            f"stderr:\n{stderr2}"
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _run_mypy_on_path(path: str) -> tuple[int, str, str]:
    """Run mypy on an arbitrary file path (for temp copies)."""
    run_env = dict(os.environ)
    pythonpath_parts = [str(_PROJECT_ROOT), str(_FIXTURES_DIR)]
    existing = run_env.get("PYTHONPATH", "")
    if existing:
        pythonpath_parts.insert(0, existing)
    run_env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    proc = subprocess.run(
        ["sage", "-python", "-m", "mypy", "--config-file", str(_CONFIG_FILE), path],
        capture_output=True,
        text=True,
        env=run_env,
        cwd=str(_PROJECT_ROOT),
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# Test: cache invalidation
# ---------------------------------------------------------------------------


def test_cache_invalidation():
    """Fresh run passes; modify ancestor; incremental run (same cache) fails."""
    cache_dir = _fresh_cache_dir()
    try:
        fixture_path = str(_fixture_module_path("test_cache_invalidation"))

        # Pass 1: fresh run with an isolated cache.
        exit_code, _, stderr = _run_mypy_cached(fixture_path, cache_dir, fresh=True)
        assert exit_code == 0, (
            f"Fresh run should pass, got {exit_code}\nstderr:\n{stderr}"
        )

        # Modify the ancestor: rename f → f_removed.
        with open(fixture_path, "r") as fh:
            original = fh.read()
        try:
            modified = original.replace(
                "def f(self) -> int:\n            \"\"\"Base method",
                "def f_removed(self) -> int:\n            \"\"\"Base method (renamed)",
            )
            with open(fixture_path, "w") as fh:
                fh.write(modified)

            # Pass 2: incremental run using the SAME cache.
            exit_code2, _, stderr2 = _run_mypy_cached(
                fixture_path, cache_dir, fresh=False
            )
            assert exit_code2 != 0, (
                f"Incremental run should fail after ancestor removal, "
                f"got {exit_code2}\nstderr:\n{stderr2}"
            )
        finally:
            # Restore the original fixture.
            with open(fixture_path, "w") as fh:
                fh.write(original)
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)


def _run_mypy_cached(
    fixture_path: str, cache_dir: str, *, fresh: bool
) -> tuple[int, str, str]:
    """Run mypy with an explicit cache directory.

    When *fresh* is True, the cache directory is cleared first.
    """
    if fresh:
        if os.path.isdir(cache_dir):
            shutil.rmtree(cache_dir)
        os.makedirs(cache_dir, exist_ok=True)

    run_env = dict(os.environ)
    pythonpath_parts = [str(_PROJECT_ROOT), str(_FIXTURES_DIR)]
    existing = run_env.get("PYTHONPATH", "")
    if existing:
        pythonpath_parts.insert(0, existing)
    run_env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    run_env["MYPY_CACHE_DIR"] = cache_dir

    proc = subprocess.run(
        [
            "sage",
            "-python",
            "-m",
            "mypy",
            "--config-file",
            str(_CONFIG_FILE),
            "--cache-dir",
            cache_dir,
            fixture_path,
        ],
        capture_output=True,
        text=True,
        env=run_env,
        cwd=str(_PROJECT_ROOT),
    )
    return proc.returncode, proc.stdout, proc.stderr
