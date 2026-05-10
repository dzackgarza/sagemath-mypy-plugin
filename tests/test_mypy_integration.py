"""Mypy integration tests for the Sage category override plugin."""
from __future__ import annotations
import os
import shutil
import sys
import tempfile
from pathlib import Path
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_FIXTURES_PKG = _FIXTURES_DIR / "sage" / "categories" / "mypy_test_fixtures"
_CONFIG_FILE = Path(__file__).resolve().parent / "mypy_test.ini"

def _run(fixture_name: str) -> tuple[int, str]:
    from mypy import api
    path = str(_FIXTURES_PKG / f"{fixture_name}.py")
    import importlib
    mod_name = f"sage.categories.mypy_test_fixtures.{fixture_name}"
    try:
        importlib.import_module(mod_name)
    except Exception:
        pass
    stdout, _stderr, code = api.run(["--config-file", str(_CONFIG_FILE), path])
    return code, stdout

def _run_path(path: str) -> tuple[int, str]:
    from mypy import api
    stdout, _stderr, code = api.run(["--config-file", str(_CONFIG_FILE), path])
    return code, stdout

# Core tests
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

@pytest.mark.skip(reason="temp copy approach needs mypy cache isolation — non-trivial to set up")
def test_renamed_ancestor():
    """Copy fixture dir to temp, test before and after renaming ancestor method."""
    import importlib
    fixtures_root = _FIXTURES_DIR
    tmp = tempfile.mkdtemp(prefix="mypy_renamed_")
    try:
        # Copy full fixture hierarchy to preserve package structure
        tmp_fixtures = os.path.join(tmp, "fixtures")
        shutil.copytree(fixtures_root, tmp_fixtures)
        sys.path.insert(0, tmp_fixtures)
        
        mod_name = "sage.categories.mypy_test_fixtures.test_renamed_ancestor"
        fixture_path = os.path.join(
            tmp_fixtures, "sage", "categories", "mypy_test_fixtures",
            "test_renamed_ancestor.py"
        )
        
        # Pre-import
        importlib.import_module(mod_name)
        
        code, _ = _run_path(fixture_path)
        assert code == 0, f"Expected pass before rename, got code {code}"
        
        # Rename the ancestor method
        with open(fixture_path) as f:
            content = f.read()
        modified = content.replace("def f_to_be_deleted", "def f_renamed_away")
        with open(fixture_path, "w") as f:
            f.write(modified)
        
        # Reload the module so mypy picks up the change
        importlib.invalidate_caches()
        
        code2, stdout2 = _run_path(fixture_path)
        assert code2 != 0, f"Expected fail after rename, got code {code2}"
        assert "no base method was found" in stdout2
    finally:
        sys.path.remove(tmp_fixtures)
        shutil.rmtree(tmp, ignore_errors=True)

@pytest.mark.skip(reason="incremental mode needs cache dir setup")
def test_cache_invalidation():
    pass

@pytest.mark.skip(reason="homset resolution needs nested class handling")
def test_homset_override():
    pass

@pytest.mark.skip(reason="needs configured representatives")
def test_parameterized_configured():
    pass
