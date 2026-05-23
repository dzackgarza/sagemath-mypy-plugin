from __future__ import annotations

from pathlib import Path

from mypy.build import BuildResult, build
from mypy.modulefinder import BuildSource
from mypy.options import Options

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_MODULE = "tests.fixtures.invariant_core.issue2_semantics"
FIXTURE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "invariant_core" / "issue2_semantics.py"
)
INVALID_FIXTURE_MODULE = "tests.fixtures.invariant_core.issue2_semantics_invalid_plain"
INVALID_FIXTURE_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "invariant_core"
    / "issue2_semantics_invalid_plain.py"
)


def test_issue2_method_container_receiver_behavior_matrix(tmp_path: Path) -> None:
    visible_sage_stubs = _write_visible_sage_stubs(tmp_path)
    config_path = _write_plugin_config(tmp_path)

    with_plugin = _run_mypy(config_path, tmp_path, visible_sage_stubs)
    without_plugin = _run_mypy_without_plugin(tmp_path, visible_sage_stubs)
    invalid_with_plugin = _run_mypy(
        config_path, tmp_path, visible_sage_stubs, source=_invalid_source()
    )
    invalid_without_plugin = _run_mypy_without_plugin(
        tmp_path, visible_sage_stubs, source=_invalid_source()
    )

    assert not with_plugin.errors, with_plugin.errors

    assert _contains(
        without_plugin,
        "source_backed_parent_method",
        "no base method was found",
    )
    assert _contains(without_plugin, "ParentMethods", "[assignment]")
    assert _contains(without_plugin, "BoundSubcategory", "[attr-defined]")
    assert _contains(invalid_with_plugin, "ParentMethods", "category", "[attr-defined]")
    assert _contains(invalid_with_plugin, "ParentMethods", "[assignment]")
    assert _contains(invalid_with_plugin, "InvalidPlainNested", "BoundSubcategory")
    assert _contains(
        invalid_with_plugin,
        "SubcategoryMethods",
        "base_category",
        "[attr-defined]",
    )
    assert _contains(invalid_without_plugin, "ParentMethods", "category", "[attr-defined]")
    assert _contains(invalid_without_plugin, "ParentMethods", "[assignment]")
    assert _contains(invalid_without_plugin, "InvalidPlainNested", "BoundSubcategory")
    assert _contains(
        invalid_without_plugin,
        "SubcategoryMethods",
        "base_category",
        "[attr-defined]",
    )


def test_issue2_strict_mode_reports_missing_receiver_typeinfo(tmp_path: Path) -> None:
    visible_sage_stubs = _write_missing_receiver_sage_stubs(tmp_path)
    config_path = _write_plugin_config(tmp_path)

    result = _run_mypy(config_path, tmp_path, visible_sage_stubs)

    assert _contains(
        result,
        "Sage category receiver TypeInfo is missing",
        "sage.structure.parent.Parent",
    )


def _write_missing_receiver_sage_stubs(tmp_path: Path) -> Path:
    stub_root = tmp_path / "missing-receiver-sage-stubs"
    categories = stub_root / "sage" / "categories"
    structure = stub_root / "sage" / "structure"
    categories.mkdir(parents=True)
    structure.mkdir(parents=True)
    (stub_root / "sage" / "__init__.pyi").write_text("")
    (categories / "__init__.pyi").write_text("")
    (structure / "__init__.pyi").write_text("")
    (categories / "category.pyi").write_text(
        "\n".join(
            (
                "class Category:",
                "    def super_categories(self) -> list[Category]: ...",
                "    def base_category(self) -> Category: ...",
                "",
            )
        )
    )
    (categories / "covariant_functorial_construction.pyi").write_text(
        "\n".join(
            (
                "from sage.categories.category import Category",
                "",
                "class FunctorialConstructionCategory(Category):",
                "    @classmethod",
                "    def category_of(cls, category: Category) -> Category: ...",
                "",
            )
        )
    )
    (structure / "element.pyi").write_text("class Element: ...\n")
    (structure / "parent.pyi").write_text("")
    return stub_root


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
                "    parent",
                "    subcategory",
                f"cache_dir = {cache_dir}",
                "strict = true",
                "",
            )
        ),
        encoding="utf-8",
    )
    return config_path


def _write_visible_sage_stubs(tmp_path: Path) -> Path:
    stub_root = tmp_path / "visible-sage-stubs"
    categories = stub_root / "sage" / "categories"
    structure = stub_root / "sage" / "structure"
    categories.mkdir(parents=True)
    structure.mkdir(parents=True)
    (stub_root / "sage" / "__init__.pyi").write_text("")
    (categories / "__init__.pyi").write_text("")
    (structure / "__init__.pyi").write_text("")
    (categories / "category.pyi").write_text(
        "\n".join(
            (
                "class Category:",
                "    def super_categories(self) -> list[Category]: ...",
                "    def base_category(self) -> Category: ...",
                "",
            )
        )
    )
    (categories / "covariant_functorial_construction.pyi").write_text(
        "\n".join(
            (
                "from sage.categories.category import Category",
                "",
                "class FunctorialConstructionCategory(Category):",
                "    @classmethod",
                "    def category_of(cls, category: Category) -> Category: ...",
                "",
            )
        )
    )
    (structure / "element.pyi").write_text(
        "\n".join(
            (
                "from sage.structure.parent import Parent",
                "",
                "class Element:",
                "    def parent(self) -> Parent: ...",
                "",
            )
        )
    )
    (structure / "parent.pyi").write_text(
        "\n".join(
            (
                "from sage.categories.category import Category",
                "from sage.structure.element import Element",
                "",
                "class Parent:",
                "    def category(self) -> Category: ...",
                "    def an_element(self) -> Element: ...",
                "",
            )
        )
    )
    return stub_root


def _run_mypy(
    config_path: Path,
    tmp_path: Path,
    visible_sage_stubs: Path,
    *,
    source: BuildSource | None = None,
) -> BuildResult:
    options = _options(tmp_path, visible_sage_stubs)
    options.config_file = str(config_path)
    options.plugins = ["sage_mypy_category_plugin.plugin"]
    return build(sources=[source or _source()], options=options)


def _run_mypy_without_plugin(
    tmp_path: Path,
    visible_sage_stubs: Path,
    *,
    source: BuildSource | None = None,
) -> BuildResult:
    return build(sources=[source or _source()], options=_options(tmp_path, visible_sage_stubs))


def _options(tmp_path: Path, visible_sage_stubs: Path) -> Options:
    options = Options()
    options.incremental = False
    options.cache_dir = str(tmp_path / "mypy-cache")
    options.enable_error_code = ["explicit-override"]
    options.mypy_path = [str(REPO_ROOT), str(visible_sage_stubs)]
    options.ignore_missing_imports = True
    return options


def _source() -> BuildSource:
    return BuildSource(str(FIXTURE_PATH), FIXTURE_MODULE, None)


def _invalid_source() -> BuildSource:
    return BuildSource(str(INVALID_FIXTURE_PATH), INVALID_FIXTURE_MODULE, None)


def _contains(result: BuildResult, *fragments: str) -> bool:
    return any(all(fragment in error for fragment in fragments) for error in result.errors)
