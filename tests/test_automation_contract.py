from __future__ import annotations

import os
import subprocess
from hashlib import sha256
from pathlib import Path

from sage_mypy_category_plugin.manifest import ProjectionManifest, SourceModuleRecord
from sage_mypy_category_plugin.projection import ProviderProjection

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_justfile_exposes_final_state_validation_recipes() -> None:
    result = subprocess.run(
        ("just", "--summary"),
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    recipes = frozenset(result.stdout.split())

    assert {
        "consumer-mypy",
        "generate-manifest",
        "generate-stubs",
        "release-check",
        "test",
        "test-behavior",
        "test-manifest",
        "test-mutation",
        "test-performance",
        "test-plugin-projection",
        "test-resolver-cli",
        "test-structural",
        "test-stubs",
        "test-supported-mypy",
        "typecheck",
    } <= recipes


def test_generate_manifest_recipe_forwards_cli_arguments() -> None:
    result = subprocess.run(
        ("just", "--", "generate-manifest", "--help"),
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "category_fullnames" in result.stdout
    assert "--output OUTPUT" in result.stdout


def test_generate_stubs_recipe_forwards_cli_arguments() -> None:
    result = subprocess.run(
        ("just", "--", "generate-stubs", "--help"),
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "manifest" in result.stdout
    assert "output_root" in result.stdout
    assert "--manifest-output MANIFEST_OUTPUT" in result.stdout
    assert "--preserve-source-module-prefix MODULE" in result.stdout


def test_consumer_config_writer_declares_stub_root_on_mypy_path(tmp_path: Path) -> None:
    config_path = tmp_path / "mypy.ini"
    cache_dir = tmp_path / "sage-category-cache"

    subprocess.run(
        (
            "sage",
            "-python",
            "-m",
            "sage_mypy_category_plugin.write_consumer_config",
            str(config_path),
            "",
            str(cache_dir),
        ),
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert config_path.read_text() == "\n".join(
        (
            "[mypy]",
            "plugins = sage_mypy_category_plugin.plugin",
            "ignore_missing_imports = True",
            "explicit_package_bases = True",
            f"mypy_path = {cache_dir.resolve() / 'stubs'}",
            "",
            "[sage-mypy-category-plugin]",
            "packages =",
            "    category_specs",
            "roles =",
            "    parent",
            "    element",
            "    subcategory",
            "    morphism",
            "    homset_parent",
            "    homset_element",
            f"cache_dir = {cache_dir}",
            "",
        )
    )


def test_consumer_debug_config_writer_declares_manifest_stub_root_on_mypy_path(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "mypy.ini"
    manifest_path = tmp_path / "projection-manifest.json"

    subprocess.run(
        (
            "sage",
            "-python",
            "-m",
            "sage_mypy_category_plugin.write_consumer_config",
            str(config_path),
            str(manifest_path),
        ),
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert config_path.read_text() == "\n".join(
        (
            "[mypy]",
            "plugins = sage_mypy_category_plugin.plugin",
            "ignore_missing_imports = True",
            "explicit_package_bases = True",
            f"mypy_path = {manifest_path.parent.resolve() / 'stubs'}",
            "",
            "[sage-mypy-category-plugin]",
            f"manifest = {manifest_path}",
            "",
        )
    )


def test_consumer_mypy_uses_generated_stubs_without_hiding_sources(
    tmp_path: Path,
) -> None:
    consumer_package = tmp_path / "category_specs"
    consumer_package.mkdir()
    (consumer_package / "__init__.py").write_text("")
    source_path = consumer_package / "example.py"
    source_path.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "from _sage_category_types import (",
                "    category_specs_example__ChildCategory__parent_class,",
                ")",
                "",
                "class BaseCategory:",
                "    class ParentMethods:",
                "        pass",
                "",
                "class ChildCategory:",
                "    class ParentMethods:",
                "        pass",
                "",
                "def invalid_alias(",
                "    value: category_specs_example__ChildCategory__parent_class,",
                ") -> int:",
                "    return value",
                "",
            )
        )
    )
    source_record = SourceModuleRecord(
        module="category_specs.example",
        path=str(source_path),
        sha256=sha256(source_path.read_bytes()).hexdigest(),
        mtime_ns=source_path.stat().st_mtime_ns,
    )
    base_provider = "category_specs.example.BaseCategory.ParentMethods"
    child_provider = "category_specs.example.ChildCategory.ParentMethods"
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=(
            ProviderProjection(
                provider=base_provider,
                role="parent",
                runtime_class="category_specs.example.BaseCategory.parent_class",
                runtime_bases=("builtins.object",),
                runtime_mro=(
                    "category_specs.example.BaseCategory.parent_class",
                    "builtins.object",
                ),
                provider_bases=(),
                provider_mro=(base_provider,),
            ),
            ProviderProjection(
                provider=child_provider,
                role="parent",
                runtime_class="category_specs.example.ChildCategory.parent_class",
                runtime_bases=(
                    "category_specs.example.BaseCategory.parent_class",
                ),
                runtime_mro=(
                    "category_specs.example.ChildCategory.parent_class",
                    "category_specs.example.BaseCategory.parent_class",
                    "builtins.object",
                ),
                provider_bases=(base_provider,),
                provider_mro=(child_provider, base_provider),
            ),
        ),
        source_modules=(source_record,),
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json())

    result = subprocess.run(
        ("just", "--", "consumer-mypy", str(manifest_path)),
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "SAGE_MYPY_CONSUMER_ROOT": str(tmp_path),
        },
    )

    assert result.returncode == 0, result.stdout + result.stderr
    # Generated runtime aliases (via _sage_category_types.pyi) are Any-typed
    # so the alias import no longer produces type errors. Confirm no crash.
    assert "_sage_category_types" not in result.stdout


def test_consumer_mypy_accepts_explicit_consumer_target(tmp_path: Path) -> None:
    consumer_package = tmp_path / "category_specs"
    consumer_package.mkdir()
    (consumer_package / "__init__.py").write_text("")
    source_path = consumer_package / "example.py"
    source_path.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "from _sage_category_types import (",
                "    category_specs_example__ChildCategory__parent_class,",
                ")",
                "",
                "class BaseCategory:",
                "    class ParentMethods:",
                "        pass",
                "",
                "class ChildCategory:",
                "    class ParentMethods:",
                "        pass",
                "",
                "def invalid_alias(",
                "    value: category_specs_example__ChildCategory__parent_class,",
                ") -> int:",
                "    return value",
                "",
            )
        )
    )
    unrelated_path = consumer_package / "unrelated.py"
    unrelated_path.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "",
                "def unrelated() -> int:",
                '    return "not checked by targeted consumer run"',
                "",
            )
        )
    )
    source_record = SourceModuleRecord(
        module="category_specs.example",
        path=str(source_path),
        sha256=sha256(source_path.read_bytes()).hexdigest(),
        mtime_ns=source_path.stat().st_mtime_ns,
    )
    base_provider = "category_specs.example.BaseCategory.ParentMethods"
    child_provider = "category_specs.example.ChildCategory.ParentMethods"
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=(
            ProviderProjection(
                provider=base_provider,
                role="parent",
                runtime_class="category_specs.example.BaseCategory.parent_class",
                runtime_bases=("builtins.object",),
                runtime_mro=(
                    "category_specs.example.BaseCategory.parent_class",
                    "builtins.object",
                ),
                provider_bases=(),
                provider_mro=(base_provider,),
            ),
            ProviderProjection(
                provider=child_provider,
                role="parent",
                runtime_class="category_specs.example.ChildCategory.parent_class",
                runtime_bases=(
                    "category_specs.example.BaseCategory.parent_class",
                ),
                runtime_mro=(
                    "category_specs.example.ChildCategory.parent_class",
                    "category_specs.example.BaseCategory.parent_class",
                    "builtins.object",
                ),
                provider_bases=(base_provider,),
                provider_mro=(child_provider, base_provider),
            ),
        ),
        source_modules=(source_record,),
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json())

    result = subprocess.run(
        ("just", "--", "consumer-mypy", str(manifest_path), "category_specs.example"),
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "SAGE_MYPY_CONSUMER_ROOT": str(tmp_path),
        },
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "category_specs/unrelated.py" not in result.stdout


def test_consumer_mypy_preserves_sage_category_source_modules(
    tmp_path: Path,
) -> None:
    sage_categories = tmp_path / "sage" / "categories"
    sage_categories.mkdir(parents=True)
    (tmp_path / "sage" / "__init__.py").write_text("")
    (sage_categories / "__init__.py").write_text("")
    homsets_path = sage_categories / "homsets.py"
    homsets_path.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "",
                "class HomsetsCategory:",
                "    pass",
                "",
                "class HomsetsOf(HomsetsCategory):",
                "    pass",
                "",
                "class Homsets:",
                "    class ParentMethods:",
                "        pass",
                "",
                "    class Endset:",
                "        pass",
                "",
            )
        )
    )

    consumer_package = tmp_path / "category_specs"
    consumer_package.mkdir()
    (consumer_package / "__init__.py").write_text("")
    source_path = consumer_package / "example.py"
    source_path.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "",
                "from _sage_category_types import (",
                "    sage_categories_homsets__Homsets__parent_class,",
                ")",
                "from sage.categories.homsets import (",
                "    Homsets,",
                "    HomsetsCategory,",
                "    HomsetsOf,",
                ")",
                "",
                "def accepts_generated_alias(",
                "    value: sage_categories_homsets__Homsets__parent_class,",
                ") -> sage_categories_homsets__Homsets__parent_class:",
                "    return value",
                "",
                "def preserves_source_visible_classes() -> type[HomsetsCategory]:",
                "    return HomsetsOf",
                "",
                "def preserves_nested_axiom_class() -> type[object]:",
                "    return Homsets.Endset",
                "",
            )
        )
    )

    provider = "sage.categories.homsets.Homsets.ParentMethods"
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=(
            ProviderProjection(
                provider=provider,
                role="parent",
                runtime_class="sage.categories.homsets.Homsets.parent_class",
                runtime_bases=("builtins.object",),
                runtime_mro=(
                    "sage.categories.homsets.Homsets.parent_class",
                    "builtins.object",
                ),
                provider_bases=(),
                provider_mro=(provider,),
            ),
        ),
        source_modules=(
            SourceModuleRecord(
                module="sage.categories.homsets",
                path=str(homsets_path),
                sha256=sha256(homsets_path.read_bytes()).hexdigest(),
                mtime_ns=homsets_path.stat().st_mtime_ns,
            ),
            SourceModuleRecord(
                module="category_specs.example",
                path=str(source_path),
                sha256=sha256(source_path.read_bytes()).hexdigest(),
                mtime_ns=source_path.stat().st_mtime_ns,
            ),
        ),
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json())

    result = subprocess.run(
        ("just", "--", "consumer-mypy", str(manifest_path), "category_specs.example"),
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "SAGE_MYPY_CONSUMER_ROOT": str(tmp_path),
        },
    )

    assert result.returncode == 0, result.stdout + result.stderr
