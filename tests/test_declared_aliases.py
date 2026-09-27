from pathlib import Path
from importlib import import_module
import os
import subprocess
import sys

def test_runtime_alias_resolves_inherited_projected_role(tmp_path: Path) -> None:
    """A projected stub may inherit the role written directly at runtime."""
    fixture = Path(__file__).parent / "fixtures" / "declared_alias_consumer"
    package = tmp_path / "projected_alias_consumer"
    package.mkdir()
    for source in fixture.glob("*.py"):
        (package / source.name).write_text(source.read_text())
    (package / "roles.pyi").write_text(
        "from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase\n"
        "class StaticRoles:\n"
        "    class ParentMethods[T = int]:\n"
        "        def echo(self, value: T) -> T: ...\n"
        "class AliasCategory(StaticRoles, LocalCategoryBase): ...\n"
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join((str(tmp_path), str(Path(__file__).resolve().parents[1])))
    for enabled in (False, True):
        config = tmp_path / "mypy.ini"
        config.write_text(
            "[mypy]\n"
            + ("plugins = sage_mypy_category_plugin.plugin\n" if enabled else "")
            + "follow_imports = silent\n"
            + f"cache_dir = {tmp_path / 'mypy-cache'}\n"
            + "[sage-mypy-category-plugin]\npackages = projected_alias_consumer\n"
            + f"cache_dir = {tmp_path / 'projection'}\n"
        )
        for valid in (True, False):
            source = tmp_path / "consumer.py"
            argument = "7" if valid else "'wrong'"
            source.write_text(
                "from projected_alias_consumer import Role\n"
                "def evaluate(value: Role[int]) -> int:\n"
                f"    return value.echo({argument})\n"
            )
            result = subprocess.run(
                [sys.executable, "-m", "mypy", "--show-traceback", "--config-file", str(config), str(source)],
                env=environment, capture_output=True, text=True, check=False,
            )
            if not enabled:
                assert result.returncode == 1, result.stdout + result.stderr
                assert "[valid-type]" in result.stdout, result.stdout
            elif valid:
                assert result.returncode == 0, result.stdout + result.stderr
            else:
                assert result.returncode == 1, result.stdout + result.stderr
                assert "[arg-type]" in result.stdout, result.stdout

def test_declared_runtime_aliases_preserve_types_with_plugin_on_and_off(tmp_path: Path) -> None:
    """Read the real Sage provider through an alias, retaining its type argument."""
    package = "tests.fixtures.declared_alias_consumer"
    assert import_module(package).Role().echo(7) == 7
    for enabled in (False, True):
        for valid in (True, False):
            directory = tmp_path / f"{enabled}-{valid}"
            directory.mkdir()
            config = directory / "mypy.ini"
            config.write_text(
                "[mypy]\n"
                + ("plugins = sage_mypy_category_plugin.plugin\n" if enabled else "")
                + "follow_imports = silent\n"
                + f"cache_dir = {tmp_path / 'mypy-cache'}\n"
                + "\n[sage-mypy-category-plugin]\n"
                + f"packages = {package}\nroles = parent\n"
                + f"cache_dir = {tmp_path / 'projection'}\n"
            )
            source = directory / "consumer.py"
            argument = "7" if valid else "'wrong'"
            source.write_text(
                f"from {package} import Role\n"
                f"from {package}.native import NativeRole\n"
                "def evaluate(value: Role[int]) -> int:\n"
                f"    return value.echo({argument})\n"
                "def evaluate_default(value: Role) -> int:\n"
                f"    return value.echo({argument})\n"
                "def evaluate_native(value: NativeRole[int]) -> int:\n"
                f"    return value.echo({argument})\n"
                + ("" if valid else
                   "def wrong_arity(value: Role[int, str]) -> None:\n    pass\n"
                   "Unreported = Role\n"
                   "def unreported(value: Unreported[int]) -> int:\n    return value.echo(7)\n")
            )
            result = subprocess.run(
                [sys.executable, "-m", "mypy", "--config-file", str(config),
                 str(source),
                 str(Path(__file__).parent / "fixtures" / "declared_alias_consumer" / "__init__.py"),
                 str(Path(__file__).parent / "fixtures" / "declared_alias_consumer" / "roles.py")],
                capture_output=True, text=True, check=False,
            )
            if not enabled:
                assert result.returncode == 1, result.stdout + result.stderr
                assert "[valid-type]" in result.stdout, result.stdout
            elif valid:
                assert result.returncode == 0, result.stdout + result.stderr
            else:
                assert result.returncode == 1, result.stdout + result.stderr
                assert result.stdout.count("[arg-type]") == 3, result.stdout
                assert "[type-arg]" in result.stdout, result.stdout
                assert result.stdout.count("[valid-type]") == 1, result.stdout
                assert 'Variable "consumer.Unreported" is not valid as a type' in result.stdout, result.stdout


def test_alias_report_changes_invalidate_source_and_projection_caches(tmp_path: Path) -> None:
    """A changed alias declaration changes real mypy results without clearing caches."""
    fixture = Path(__file__).parent / "fixtures" / "declared_alias_consumer"
    package = tmp_path / "alias_cache_consumer"
    package.mkdir()
    for source in fixture.glob("*.py"):
        (package / source.name).write_text(source.read_text())
    roles = package / "roles.py"
    roles.write_text(roles.read_text() + "\nclass AlternateCategory(AliasCategory):\n"
                     "    class ParentMethods[T]:\n"
                     "        def echo(self, value: str) -> str:\n"
                     "            return value\n")
    config = tmp_path / "mypy.ini"
    config.write_text(
        "[mypy]\nplugins = sage_mypy_category_plugin.plugin\n"
        "follow_imports = silent\n"
        f"cache_dir = {tmp_path / 'mypy-cache'}\n"
        "[sage-mypy-category-plugin]\npackages = alias_cache_consumer\n"
        f"cache_dir = {tmp_path / 'projection'}\n"
    )
    source = tmp_path / "consumer.py"
    source.write_text("from alias_cache_consumer import Role\n"
                      "def evaluate(value: Role[int]) -> int:\n"
                      "    return value.echo(7)\n")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join((str(tmp_path), str(Path(__file__).resolve().parents[1])))
    command = [sys.executable, "-m", "mypy", "--config-file", str(config), str(source)]
    first = subprocess.run(command, env=environment, capture_output=True, text=True, check=False)
    assert first.returncode == 0, first.stdout + first.stderr
    declaration = package / "__init__.py"
    declaration.write_text(declaration.read_text().replace("roles.AliasCategory", "roles.AlternateCategory"))
    second = subprocess.run(command, env=environment, capture_output=True, text=True, check=False)
    assert second.returncode == 1, second.stdout + second.stderr
    assert "[arg-type]" in second.stdout, second.stdout
    assert "[return-value]" in second.stdout, second.stdout
    declaration.write_text(declaration.read_text().replace("def declared_type_aliases(", "def missing_alias_report("))
    missing = subprocess.run(command, env=environment, capture_output=True, text=True, check=False)
    assert missing.returncode != 0, missing.stdout + missing.stderr
    assert "The declaring compiler must report declared_type_aliases()" in missing.stdout + missing.stderr, missing.stdout + missing.stderr
