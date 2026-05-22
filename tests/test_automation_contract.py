from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PACKAGE = REPO_ROOT / "sage_mypy_category_plugin"
SAGE_STUBS_COMMIT = "1bb285047beacbdd2b44fef011233b024e8f7631"


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
        "generate-manifest",
        "release-check",
        "test",
        "test-behavior",
        "test-manifest",
        "test-mutation",
        "test-performance",
        "test-plugin-projection",
        "test-production-lifecycle",
        "test-resolver-cli",
        "test-structural",
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


def test_production_validation_recipes_do_not_expose_wrapper_or_stub_generation() -> None:
    result = subprocess.run(
        ("just", "--summary"),
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    recipes = frozenset(result.stdout.split())

    assert "consumer-mypy" not in recipes
    assert "generate-stubs" not in recipes
    assert "test-stubs" not in recipes


def test_release_check_runs_final_architecture_gates() -> None:
    justfile = (REPO_ROOT / "justfile").read_text(encoding="utf-8")
    release_check = justfile.split("[group('test')]\nrelease-check:", maxsplit=1)[1]
    release_check = release_check.split("\n[group(", maxsplit=1)[0]

    assert "just test-performance" in release_check
    assert "just test-structural -q" in release_check
    assert "just test-manifest -q" in release_check
    assert "just test-production-lifecycle -q" in release_check
    assert "just test-plugin-projection -q" in release_check
    assert "just test-behavior -q" in release_check
    assert "just test tests/test_automation_contract.py -q" in release_check
    assert "consumer-structural" not in release_check
    assert "just test-supported-mypy" in release_check
    assert "just test-mutation" in release_check


def test_consumer_config_writer_is_not_installed_plugin_surface() -> None:
    assert not (PLUGIN_PACKAGE / "write_consumer_config.py").exists()


def test_generated_stub_modules_are_not_installed_plugin_surface() -> None:
    assert not (PLUGIN_PACKAGE / "stubs.py").exists()
    assert not (PLUGIN_PACKAGE / "static_stubs.py").exists()


def test_readme_documents_only_package_mode_user_config() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "manifest = " not in readme
    assert "mypy_path = .mypy_cache/sage-category-plugin/stubs" not in readme
    assert "packages =" in readme
    assert "sage-stubs" in readme


def test_sidecar_install_paths_pin_exact_sage_stubs_commit() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    sidecar_extra = project["project"]["optional-dependencies"]["sage10_7"]
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    justfile = (REPO_ROOT / "justfile").read_text(encoding="utf-8")

    expected_url = f"git+https://github.com/dzackgarza/sage-stubs@{SAGE_STUBS_COMMIT}"

    assert sidecar_extra == [f"sage-stubs @ {expected_url}"]
    assert expected_url in readme
    assert expected_url in justfile


def test_plugin_init_does_not_generate_or_expose_upstream_sage_stubs() -> None:
    plugin_source = (PLUGIN_PACKAGE / "plugin.py").read_text(encoding="utf-8")

    assert "write_generated_stub_tree" not in plugin_source
    assert "_generate_and_write_stubs" not in plugin_source
    assert "_add_generated_stubs_to_mypy_path" not in plugin_source
    assert "cache_dir/stubs" not in plugin_source


def test_plugin_config_does_not_accept_pre_generated_manifest_option() -> None:
    plugin_source = (PLUGIN_PACKAGE / "plugin.py").read_text(encoding="utf-8")

    assert "debug_manifest" not in plugin_source
    assert 'has_option(CONFIG_SECTION, "manifest")' not in plugin_source


# ---------------------------------------------------------------------------
# CONTRACT.md sentinel checks — automated enforcement of banned patterns
# ---------------------------------------------------------------------------

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


def test_contract_no_bare_except_exception_in_plugin_package() -> None:
    """CONTRACT.md BP3: bare 'except Exception' is banned in the plugin package.

    BP3 forbids silent exception swallowing in projection paths.  Every caught
    exception must either be specific (e.g. AttributeError, ModuleNotFoundError)
    or logged at DEBUG level.  A bare 'except Exception' clause with no logging
    makes failures indistinguishable from 'no projection needed', masking real
    bugs.  The only approved broad catches are the two guarded oracle import loops
    which explicitly use narrower types (AttributeError, TypeError, ValueError,
    AssertionError) and log at DEBUG level.

    This test ensures 'except Exception' never appears in the plugin package,
    even accidentally via a refactor that widens an existing catch.
    """
    hits = _rg_count(r"\bexcept\s+Exception\b", PLUGIN_PACKAGE)
    assert hits == [], (
        "Found bare 'except Exception' in plugin package — "
        "CONTRACT.md BP3 forbids silent exception swallowing; "
        "use a specific exception type and log at DEBUG level:\n"
        + "\n".join(hits)
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
