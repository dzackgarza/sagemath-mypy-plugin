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

    assert result.returncode == 1, result.stdout + result.stderr
    assert "category_specs/example.py" in result.stdout
    assert "Incompatible return value type" in result.stdout
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

    assert result.returncode == 1, result.stdout + result.stderr
    assert "category_specs/example.py" in result.stdout
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


# ---------------------------------------------------------------------------
# CONTRACT.md sentinel checks — automated enforcement of banned patterns
# ---------------------------------------------------------------------------

PLUGIN_PACKAGE = REPO_ROOT / "sage_mypy_category_plugin"


def _rg_count(pattern: str, path: Path) -> list[str]:
    """Return lines from ripgrep that match pattern in path, or [] if none."""
    result = subprocess.run(
        ("rg", "-n", "--no-heading", pattern, str(path)),
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def test_contract_no_diagnostic_filter_functions_in_plugin_package() -> None:
    """CONTRACT.md I2/BP2: plugin must not filter mypy diagnostics.

    Any function named _filter* in the plugin package would indicate a suppression
    path. Only registered suppressions in GOALS.md are permitted, and those must be
    implemented without broad filter functions.
    """
    hits = _rg_count(r"def _filter", PLUGIN_PACKAGE)
    assert hits == [], (
        "Found diagnostic filter function(s) in plugin package — "
        "CONTRACT.md I2 forbids filtering mypy diagnostics:\n"
        + "\n".join(hits)
    )


def test_contract_no_sage_categories_namespace_strings_in_plugin_package() -> None:
    """CONTRACT.md I3/BP1: plugin must not hardcode 'sage.categories.' as a string.

    Resolution logic must use runtime introspection, not string matching on
    namespace prefixes.
    """
    hits = _rg_count(r'"sage\.categories\.', PLUGIN_PACKAGE)
    assert hits == [], (
        "Found hardcoded 'sage.categories.' string in plugin package — "
        "CONTRACT.md I3 forbids namespace-specific string matching:\n"
        + "\n".join(hits)
    )


def test_contract_no_consumer_namespace_strings_in_plugin_package() -> None:
    """CONTRACT.md I3/BP1: plugin must not hardcode 'category_specs' or any
    consumer package name as a string.
    """
    hits = _rg_count(r'"category_specs', PLUGIN_PACKAGE)
    assert hits == [], (
        "Found hardcoded 'category_specs' string in plugin package — "
        "CONTRACT.md I3 forbids consumer namespace hardcoding:\n"
        + "\n".join(hits)
    )


def test_contract_no_banned_broad_hooks_in_plugin() -> None:
    """CONTRACT.md BP7: the plugin core must only register the three approved hooks.

    get_function_hook, get_method_hook, get_attribute_hook, and get_base_class_hook
    may only appear with explicit justification in GOALS.md Suppression Registry.
    """
    plugin_file = PLUGIN_PACKAGE / "plugin.py"
    hits = _rg_count(
        r"get_function_hook|get_method_hook|get_attribute_hook|get_base_class_hook",
        plugin_file,
    )
    assert hits == [], (
        "Found banned broad hook(s) in plugin.py — "
        "CONTRACT.md BP7 restricts hooks to get_customize_class_mro_hook, "
        "get_additional_deps, and report_config_data:\n"
        + "\n".join(hits)
    )


def test_contract_no_unconditional_skip_markers_in_tests() -> None:
    """CONTRACT.md BP10: @pytest.mark.skip and @pytest.mark.skipif are banned.

    Unconditional skips hide real failures and violate the 'no masking' rule.
    Tests must reflect 100% actual runtime reality. There is no approved use of
    skip or skipif in this repo.
    """
    tests_dir = REPO_ROOT / "tests"
    # Match only decorator lines: leading whitespace then @pytest.mark.skip/skipif
    hits = _rg_count(r"^\s*@pytest\.mark\.(skip|skipif)\b", tests_dir)
    assert hits == [], (
        "Found @pytest.mark.skip or @pytest.mark.skipif in tests — "
        "CONTRACT.md BP10 bans unconditional skips:\n"
        + "\n".join(hits)
    )


def test_contract_no_xfail_without_strict_in_tests() -> None:
    """CONTRACT.md BP10: @pytest.mark.xfail may only be used with strict=True.

    A non-strict xfail can silently pass when the underlying failure disappears,
    turning the test into dead verification. Any xfail that omits strict=True
    or uses strict=False is banned. Additionally the xfail must document a
    deletion condition in its 'reason' argument (enforced by code review; this
    test only enforces the strict= requirement mechanically).
    """
    tests_dir = REPO_ROOT / "tests"
    # Match @pytest.mark.xfail lines that lack strict=True.
    # A line with strict=True is acceptable; one without it is banned.
    # Match only decorator lines: leading whitespace then @pytest.mark.xfail
    xfail_hits = _rg_count(r"^\s*@pytest\.mark\.xfail\b", tests_dir)
    non_strict_hits = [
        line for line in xfail_hits if "strict=True" not in line
    ]
    assert non_strict_hits == [], (
        "Found @pytest.mark.xfail without strict=True — "
        "CONTRACT.md BP10 requires strict=True and a documented deletion condition:\n"
        + "\n".join(non_strict_hits)
    )


def test_contract_fixtures_use_local_wrapper_not_direct_sage_category() -> None:
    """CONTRACT.md BP2: test fixtures for third-party namespace tests must inherit
    from a local wrapper base, not from sage.categories.category.Category directly.

    Fixtures that inherit from Sage Category directly pass Sage's runtime
    introspection even when the plugin's namespace handling is completely broken,
    producing false greens. The local_wrapper.py itself is exempt — it IS the
    permitted wrapper base.
    """
    fixtures_dir = REPO_ROOT / "tests" / "fixtures"
    hits = _rg_count(r"class \w+\(Category\)", fixtures_dir)
    # The only permitted Category base in fixture code is the local cat wrapper
    # (tests.fixtures.invariant_core.category_specs_like.cat.Category), not the
    # bare Sage Category. Filter out lines that import from the local cat package.
    direct_sage_hits = [
        line
        for line in hits
        if "category_specs_like" not in line
    ]
    assert direct_sage_hits == [], (
        "Found fixture class(es) inheriting directly from Category — "
        "CONTRACT.md BP2: use LocalCategoryBase or the category_specs_like "
        "local Category wrapper instead:\n"
        + "\n".join(direct_sage_hits)
    )
