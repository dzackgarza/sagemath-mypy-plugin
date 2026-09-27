from pathlib import Path
import subprocess
import sys

from tests.fixtures.declared_alias_consumer import Role


def test_declared_runtime_aliases_preserve_types_with_plugin_on_and_off(tmp_path: Path) -> None:
    """Read the real Sage provider through an alias, retaining its type argument."""
    assert Role().echo(7) == 7
    package = "tests.fixtures.declared_alias_consumer"
    for enabled in (False, True):
        for valid in (True, False):
            directory = tmp_path / f"{enabled}-{valid}"
            directory.mkdir()
            config = directory / "mypy.ini"
            config.write_text(
                "[mypy]\n"
                + ("plugins = sage_mypy_category_plugin.plugin\n" if enabled else "")
                + "follow_imports = silent\n"
                + "\n[sage-mypy-category-plugin]\n"
                + f"packages = {package}\nroles = parent\n"
                + f"cache_dir = {directory / 'projection'}\n"
            )
            source = directory / "consumer.py"
            argument = "7" if valid else "'wrong'"
            source.write_text(
                f"from {package} import Role\n"
                "def evaluate(value: Role[int]) -> int:\n"
                f"    return value.echo({argument})\n"
            )
            result = subprocess.run(
                [sys.executable, "-m", "mypy", "--config-file", str(config),
                 "--no-incremental", str(source)],
                capture_output=True, text=True, check=False,
            )
            if not enabled:
                assert result.returncode == 1, result.stdout + result.stderr
                assert "[valid-type]" in result.stdout, result.stdout
            elif valid:
                assert result.returncode == 0, result.stdout + result.stderr
            else:
                assert result.returncode == 1, result.stdout + result.stderr
                assert "[arg-type]" in result.stdout, result.stdout
                assert "[valid-type]" not in result.stdout, result.stdout
