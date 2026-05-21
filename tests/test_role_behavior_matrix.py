from __future__ import annotations

from pathlib import Path

from mypy.build import BuildResult, build
from mypy.modulefinder import BuildSource
from mypy.options import Options

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "invariant_core"

ROLE_BEHAVIOR_CASES = {
    "element_valid": (
        "tests.fixtures.invariant_core.role_behavior_element_valid",
        "tests.fixtures.invariant_core.role_behavior_element_valid.ValidElementOverrideCategory",
    ),
    "element_invalid": (
        "tests.fixtures.invariant_core.role_behavior_element_invalid",
        "tests.fixtures.invariant_core.role_behavior_element_invalid.InvalidElementOverrideCategory",
    ),
    "subcategory_valid": (
        "tests.fixtures.invariant_core.role_behavior_subcategory_valid",
        "tests.fixtures.invariant_core.role_behavior_subcategory_valid.ValidSubcategoryOverrideCategory",
    ),
    "subcategory_invalid": (
        "tests.fixtures.invariant_core.role_behavior_subcategory_invalid",
        "tests.fixtures.invariant_core.role_behavior_subcategory_invalid.InvalidSubcategoryOverrideCategory",
    ),
    "morphism_valid": (
        "tests.fixtures.invariant_core.role_behavior_morphism_valid",
        "tests.fixtures.invariant_core.role_behavior_morphism_valid.ValidMorphismOverrideCategory",
    ),
    "morphism_invalid": (
        "tests.fixtures.invariant_core.role_behavior_morphism_invalid",
        "tests.fixtures.invariant_core.role_behavior_morphism_invalid.InvalidMorphismOverrideCategory",
    ),
    "homset_parent_valid": (
        "tests.fixtures.invariant_core.role_behavior_homset_parent_valid",
        "tests.fixtures.invariant_core.role_behavior_homset_parent_valid.ValidHomsetParentOverrideCategory",
    ),
    "homset_parent_invalid": (
        "tests.fixtures.invariant_core.role_behavior_homset_parent_invalid",
        "tests.fixtures.invariant_core.role_behavior_homset_parent_invalid.InvalidHomsetParentOverrideCategory",
    ),
    "homset_element_valid": (
        "tests.fixtures.invariant_core.role_behavior_homset_element_valid",
        "tests.fixtures.invariant_core.role_behavior_homset_element_valid.ValidHomsetElementOverrideCategory",
    ),
    "homset_element_invalid": (
        "tests.fixtures.invariant_core.role_behavior_homset_element_invalid",
        "tests.fixtures.invariant_core.role_behavior_homset_element_invalid.InvalidHomsetElementOverrideCategory",
    ),
}

def test_non_parent_role_behavior_matrix_uses_standard_mypy_inheritance_rules(
    tmp_path: Path,
) -> None:
    visible_sage_stubs = _write_visible_sage_homset_stubs(tmp_path)
    config_path = _write_plugin_config(tmp_path)

    with_plugin = _run_mypy(
        tuple(case[0] for case in ROLE_BEHAVIOR_CASES.values()),
        config_path,
        tmp_path,
        mypy_path_entries=(REPO_ROOT, visible_sage_stubs),
    )
    without_plugin = _run_mypy_without_plugin(
        tuple(case[0] for case in ROLE_BEHAVIOR_CASES.values()),
        tmp_path,
        mypy_path_entries=(REPO_ROOT, visible_sage_stubs),
    )

    assert not _case_errors(with_plugin, "element_valid")
    assert _case_contains(without_plugin, "element_valid", "no base method was found")
    assert _case_contains(with_plugin, "element_invalid", "no base method was found")
    assert _case_contains(without_plugin, "element_invalid", "no base method was found")

    assert not _case_errors(with_plugin, "subcategory_valid")
    assert _case_contains(without_plugin, "subcategory_valid", "no base method was found")
    assert _case_contains(with_plugin, "subcategory_invalid", "no base method was found")
    assert _case_contains(without_plugin, "subcategory_invalid", "no base method was found")

    assert not _case_errors(with_plugin, "morphism_valid")
    assert _case_contains(without_plugin, "morphism_valid", "no base method was found")
    assert _case_contains(with_plugin, "morphism_invalid", "no base method was found")
    assert _case_contains(without_plugin, "morphism_invalid", "no base method was found")

    assert not _case_errors(with_plugin, "homset_parent_valid")
    assert _case_contains(
        without_plugin,
        "homset_parent_valid",
        "no base method was found",
    )
    assert _case_contains(
        with_plugin,
        "homset_parent_invalid",
        "no base method was found",
    )
    assert _case_contains(
        without_plugin,
        "homset_parent_invalid",
        "no base method was found",
    )

    assert not _case_errors(with_plugin, "homset_element_valid")
    assert _case_contains(
        without_plugin,
        "homset_element_valid",
        "no base method was found",
    )
    assert _case_contains(
        with_plugin,
        "homset_element_invalid",
        "no base method was found",
    )
    assert _case_contains(
        without_plugin,
        "homset_element_invalid",
        "no base method was found",
    )


def _write_plugin_config(tmp_path: Path) -> Path:
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core",
                "roles =",
                "    element",
                "    subcategory",
                "    morphism",
                "    homset_parent",
                "    homset_element",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    return config_path

def _write_visible_sage_homset_stubs(tmp_path: Path) -> Path:
    stub_root = tmp_path / "visible-sage-stubs"
    categories = stub_root / "sage" / "categories"
    categories.mkdir(parents=True)
    (stub_root / "sage" / "__init__.pyi").write_text("")
    (categories / "__init__.pyi").write_text("")
    (categories / "homsets.pyi").write_text(
        "\n".join(
            (
                "class HomsetsCategory: ...",
                "class Homsets:",
                "    class ParentMethods:",
                "        def top_homset_parent(self) -> int: ...",
                "",
            )
        )
    )
    (categories / "sets_cat.pyi").write_text(
        "\n".join(
            (
                "class Sets:",
                "    class ParentMethods:",
                "        def top_homset_parent(self) -> int: ...",
                "    class ElementMethods:",
                "        def top_homset_element(self) -> int: ...",
                "",
            )
        )
    )
    (categories / "objects.pyi").write_text(
        "\n".join(
            (
                "class Objects:",
                "    class ParentMethods:",
                "        def top_homset_parent(self) -> int: ...",
                "",
            )
        )
    )
    return stub_root


def _run_mypy(
    modules: tuple[str, ...],
    config_path: Path,
    tmp_path: Path,
    *,
    mypy_path_entries: tuple[Path, ...] = (REPO_ROOT,),
) -> BuildResult:
    options = _options(tmp_path)
    options.config_file = str(config_path)
    options.plugins = ["sage_mypy_category_plugin.plugin"]
    options.mypy_path = [str(path) for path in mypy_path_entries]
    return build(sources=[_source(module) for module in modules], options=options)


def _run_mypy_without_plugin(
    modules: tuple[str, ...],
    tmp_path: Path,
    *,
    mypy_path_entries: tuple[Path, ...] = (REPO_ROOT,),
) -> BuildResult:
    options = _options(tmp_path)
    options.mypy_path = [str(path) for path in mypy_path_entries]
    return build(sources=[_source(module) for module in modules], options=options)


def _options(tmp_path: Path) -> Options:
    options = Options()
    options.incremental = False
    options.cache_dir = str(tmp_path / "mypy-cache")
    options.mypy_path = [str(REPO_ROOT)]
    options.ignore_missing_imports = True
    return options


def _source(module: str) -> BuildSource:
    return BuildSource(str(_module_path(module)), module, None)


def _module_path(module: str) -> Path:
    filename = module.rsplit(".", maxsplit=1)[-1] + ".py"
    return FIXTURE_ROOT / filename


def _case_contains(result: BuildResult, case_name: str, fragment: str) -> bool:
    return any(fragment in error for error in _case_errors(result, case_name))


def _case_errors(result: BuildResult, case_name: str) -> tuple[str, ...]:
    filename = _module_path(ROLE_BEHAVIOR_CASES[case_name][0]).name
    return tuple(error for error in result.errors if filename in error)
