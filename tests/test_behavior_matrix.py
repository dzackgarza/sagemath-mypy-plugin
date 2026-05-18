from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from importlib import import_module
from pathlib import Path

from mypy.build import BuildResult, build
from mypy.modulefinder import BuildSource
from mypy.options import Options

from sage_mypy_category_plugin.manifest import (
    ProjectionManifest,
    SourceModuleRecord,
    write_manifest,
)
from sage_mypy_category_plugin.oracle import provider_projections_for_categories

type SourceTree = dict[str, "SourceTree"]

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "invariant_core"
BASE_CATEGORY_FULLNAMES = (
    "tests.fixtures.invariant_core.diamond_runtime.TopCategory",
    "tests.fixtures.invariant_core.diamond_runtime.LeftCategory",
    "tests.fixtures.invariant_core.diamond_runtime.RightCategory",
    "tests.fixtures.invariant_core.diamond_runtime.BottomCategory",
)
COMMUTATIVE_RINGS_CATEGORY = "sage.categories.commutative_rings.CommutativeRings"
COMMUTATIVE_RINGS_PROVIDER = (
    "sage.categories.commutative_rings.CommutativeRings.ParentMethods"
)
RINGS_PROVIDER = "sage.categories.rings.Rings.ParentMethods"
FUNCTORIAL_CARTESIAN_CATEGORY = (
    "tests.fixtures.invariant_core.functorial.cartesian_products."
    "CartesianProductsCategory"
)
SETS_PROVIDER = "sage.categories.sets_cat.Sets.ParentMethods"
FUNCTORIAL_CARTESIAN_PARENT_PROVIDER = (
    "sage.categories.sets_cat.Sets.CartesianProducts.ParentMethods"
)
PARAMETERIZED_CATEGORY_FULLNAMES = (
    "tests.fixtures.invariant_core.parameterized.ModulesOverIntegers",
    "tests.fixtures.invariant_core.parameterized.ModulesOverRationals",
    "tests.fixtures.invariant_core.parameterized.VectorSpacesOverRationals",
)
MODULES_PROVIDER = "sage.categories.modules.Modules.ParentMethods"
VECTOR_SPACES_PROVIDER = "sage.categories.vector_spaces.VectorSpaces.ParentMethods"
BEHAVIOR_CASES = {
    "valid": (
        "tests.fixtures.invariant_core.diamond_behavior_valid",
        "tests.fixtures.invariant_core.diamond_behavior_valid.ValidOverrideCategory",
    ),
    "invalid": (
        "tests.fixtures.invariant_core.diamond_behavior_invalid",
        "tests.fixtures.invariant_core.diamond_behavior_invalid.InvalidOverrideCategory",
    ),
    "final": (
        "tests.fixtures.invariant_core.diamond_behavior_final_violation",
        "tests.fixtures.invariant_core.diamond_behavior_final_violation.FinalBaseCategory",
        "tests.fixtures.invariant_core.diamond_behavior_final_violation.FinalViolationCategory",
    ),
    "signature": (
        "tests.fixtures.invariant_core.diamond_behavior_signature_mismatch",
        "tests.fixtures.invariant_core.diamond_behavior_signature_mismatch.SignatureBaseCategory",
        "tests.fixtures.invariant_core.diamond_behavior_signature_mismatch.SignatureMismatchCategory",
    ),
    "missing_explicit_override": (
        "tests.fixtures.invariant_core.diamond_behavior_missing_explicit_override",
        "tests.fixtures.invariant_core.diamond_behavior_missing_explicit_override.MissingExplicitOverrideCategory",
    ),
}


def test_behavior_matrix_uses_standard_mypy_inheritance_rules(tmp_path: Path) -> None:
    config_path = _write_plugin_config(tmp_path)

    with_plugin = _run_mypy(
        tuple(case[0] for case in BEHAVIOR_CASES.values()),
        config_path,
        tmp_path,
    )
    without_plugin = _run_mypy_without_plugin(
        tuple(case[0] for case in BEHAVIOR_CASES.values()),
        tmp_path,
    )

    assert not _case_errors(with_plugin, "valid")
    assert _case_contains(without_plugin, "valid", "no base method was found")
    assert _case_contains(with_plugin, "invalid", "no base method was found")
    assert _case_contains(without_plugin, "invalid", "no base method was found")
    assert _case_contains(with_plugin, "final", "Cannot override final attribute")
    assert _case_contains(without_plugin, "final", "no base method was found")
    assert _case_contains(with_plugin, "signature", 'Argument 1 of "signature_method"')
    assert _case_contains(with_plugin, "signature", "[override]")
    assert _case_contains(without_plugin, "signature", "no base method was found")
    assert _case_contains(with_plugin, "missing_explicit_override", "[explicit-override]")
    assert not _case_errors(without_plugin, "missing_explicit_override")


def test_nested_sage_provider_behavior_matrix_uses_standard_mypy_rules(
    tmp_path: Path,
) -> None:
    with_plugin = _run_nested_provider_mypy(tmp_path, with_plugin=True)
    without_plugin = _run_nested_provider_mypy(tmp_path, with_plugin=False)

    assert not _contains_error(with_plugin, '"is_commutative"')
    assert not _contains_error(with_plugin, '"construction"')
    assert not _contains_error(with_plugin, '"tensor_square"')
    assert _contains_error_fragments(
        with_plugin,
        '"not_a_sage_axiom_method"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        with_plugin,
        '"not_a_sage_functorial_method"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        with_plugin,
        '"not_a_sage_parameterized_method"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        without_plugin,
        '"is_commutative"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        without_plugin,
        '"construction"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        without_plugin,
        '"tensor_square"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        without_plugin,
        '"not_a_sage_axiom_method"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        without_plugin,
        '"not_a_sage_functorial_method"',
        "no base method was found",
    )
    assert _contains_error_fragments(
        without_plugin,
        '"not_a_sage_parameterized_method"',
        "no base method was found",
    )


def _write_plugin_config(tmp_path: Path) -> Path:
    category_fullnames = list(BASE_CATEGORY_FULLNAMES)
    for case in BEHAVIOR_CASES.values():
        category_fullnames.extend(case[1:])
    projections = provider_projections_for_categories(
        tuple(category_fullnames),
        roles=("parent",),
    )
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
    )
    manifest_path = tmp_path / "sage-category-projections.json"
    config_path = tmp_path / "mypy.ini"
    write_manifest(manifest_path, manifest)
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )
    return config_path


def _run_nested_provider_mypy(
    tmp_path: Path,
    *,
    with_plugin: bool,
) -> BuildResult:
    source_root = tmp_path / "nested-providers"
    axiom_projections = provider_projections_for_categories(
        (COMMUTATIVE_RINGS_CATEGORY,),
        roles=("parent",),
    )
    functorial_projections = provider_projections_for_categories(
        (FUNCTORIAL_CARTESIAN_CATEGORY,),
        roles=("parent",),
    )
    parameterized_projections = provider_projections_for_categories(
        PARAMETERIZED_CATEGORY_FULLNAMES,
        roles=("parent",),
    )
    projections = {
        **axiom_projections,
        **functorial_projections,
        **parameterized_projections,
    }
    provider_mro = tuple(
        dict.fromkeys(
            (
                *axiom_projections[COMMUTATIVE_RINGS_PROVIDER].provider_mro,
                *functorial_projections[
                    FUNCTORIAL_CARTESIAN_PARENT_PROVIDER
                ].provider_mro,
                *parameterized_projections[VECTOR_SPACES_PROVIDER].provider_mro,
            )
        )
    )
    source_modules = _write_nested_provider_sources(
        source_root,
        providers=provider_mro,
    )
    config_path = tmp_path / "nested-provider-mypy.ini"
    manifest_path = tmp_path / "nested-provider-manifest.json"
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
        source_modules=source_modules,
    )
    write_manifest(manifest_path, manifest)
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )

    options = Options()
    options.incremental = False
    options.cache_dir = str(tmp_path / f"{with_plugin}-mypy-cache")
    options.mypy_path = [str(source_root)]
    options.ignore_missing_imports = True
    if with_plugin:
        options.config_file = str(config_path)
        options.plugins = ["sage_mypy_category_plugin.plugin"]
    return build(
        sources=[
            BuildSource(
                str(source_root / "sage" / "categories" / "commutative_rings.py"),
                "sage.categories.commutative_rings",
                None,
            ),
            BuildSource(
                str(source_root / "sage" / "categories" / "sets_cat.py"),
                "sage.categories.sets_cat",
                None,
            ),
            BuildSource(
                str(source_root / "sage" / "categories" / "vector_spaces.py"),
                "sage.categories.vector_spaces",
                None,
            ),
        ],
        options=options,
    )


def _write_nested_provider_sources(
    source_root: Path,
    *,
    providers: tuple[str, ...],
) -> tuple[SourceModuleRecord, ...]:
    module_trees: dict[str, SourceTree] = defaultdict(dict)
    for provider in providers:
        module_name, qualname = _importable_module_and_qualname(provider)
        _add_qualname(module_trees[module_name], qualname)

    method_bodies = {
        _importable_module_and_qualname(RINGS_PROVIDER): (
            "def is_commutative(self) -> bool:",
            "    return False",
        ),
        _importable_module_and_qualname(SETS_PROVIDER): (
            "def construction(self) -> str:",
            '    return "sets"',
        ),
        _importable_module_and_qualname(MODULES_PROVIDER): (
            "def tensor_square(self) -> str:",
            '    return "module tensor square"',
        ),
        _importable_module_and_qualname(COMMUTATIVE_RINGS_PROVIDER): (
            "@override",
            "def is_commutative(self) -> bool:",
            "    return True",
            "",
            "@override",
            "def not_a_sage_axiom_method(self) -> bool:",
            "    return True",
        ),
        _importable_module_and_qualname(FUNCTORIAL_CARTESIAN_PARENT_PROVIDER): (
            "@override",
            "def construction(self) -> str:",
            '    return "cartesian products"',
            "",
            "@override",
            "def not_a_sage_functorial_method(self) -> str:",
            '    return "invalid"',
        ),
        _importable_module_and_qualname(VECTOR_SPACES_PROVIDER): (
            "@override",
            "def tensor_square(self) -> str:",
            '    return "vector space tensor square"',
            "",
            "@override",
            "def not_a_sage_parameterized_method(self) -> str:",
            '    return "invalid"',
        ),
    }
    source_modules: list[SourceModuleRecord] = []
    for package_dir in (
        source_root / "sage",
        source_root / "sage" / "categories",
    ):
        package_dir.mkdir(parents=True, exist_ok=True)
        (package_dir / "__init__.py").write_text("")

    for module_name, tree in sorted(module_trees.items()):
        path = source_root.joinpath(*module_name.split(".")).with_suffix(".py")
        path.parent.mkdir(parents=True, exist_ok=True)
        source = "\n".join(
            (
                "from typing import override",
                "",
                *_source_lines(tree, method_bodies, module_name=module_name),
            )
        )
        path.write_text(source + "\n")
        source_modules.append(
            SourceModuleRecord(
                module=module_name,
                path=str(path),
                sha256=sha256((source + "\n").encode()).hexdigest(),
            )
        )
    return tuple(source_modules)


def _importable_module_and_qualname(fullname: str) -> tuple[str, tuple[str, ...]]:
    parts = fullname.split(".")
    for split_index in range(len(parts), 0, -1):
        module_name = ".".join(parts[:split_index])
        try:
            import_module(module_name)
        except ModuleNotFoundError:
            continue
        return module_name, tuple(parts[split_index:])
    raise AssertionError(f"Could not find importable module for {fullname!r}")


def _add_qualname(tree: SourceTree, qualname: tuple[str, ...]) -> None:
    current = tree
    for name in qualname:
        current = current.setdefault(name, {})


def _source_lines(
    tree: SourceTree,
    method_bodies: dict[tuple[str, tuple[str, ...]], tuple[str, ...]],
    *,
    module_name: str | None = None,
    qualname: tuple[str, ...] = (),
    indent: int = 0,
) -> tuple[str, ...]:
    lines: list[str] = []
    for name, child in sorted(
        tree.items(),
        key=lambda item: (item[0] != "ParentMethods", item[0]),
    ):
        nested_qualname = (*qualname, name)
        lines.append(f"{'    ' * indent}class {name}:")
        if child:
            lines.extend(
                _source_lines(
                    child,
                    method_bodies,
                    module_name=module_name,
                    qualname=nested_qualname,
                    indent=indent + 1,
                )
            )
            continue

        body = method_bodies.get((module_name or "", nested_qualname), ("pass",))
        lines.extend(f"{'    ' * (indent + 1)}{line}" for line in body)
    return tuple(lines)


def _run_mypy(
    modules: tuple[str, ...],
    config_path: Path,
    tmp_path: Path,
) -> BuildResult:
    options = _options(tmp_path)
    options.config_file = str(config_path)
    options.plugins = ["sage_mypy_category_plugin.plugin"]
    return build(sources=[_source(module) for module in modules], options=options)


def _run_mypy_without_plugin(modules: tuple[str, ...], tmp_path: Path) -> BuildResult:
    return build(sources=[_source(module) for module in modules], options=_options(tmp_path))


def _options(tmp_path: Path) -> Options:
    options = Options()
    options.incremental = False
    options.cache_dir = str(tmp_path / "mypy-cache")
    options.enable_error_code = ["explicit-override"]
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


def _contains_error(result: BuildResult, fragment: str) -> bool:
    return any(fragment in error for error in result.errors)


def _contains_error_fragments(result: BuildResult, *fragments: str) -> bool:
    return any(
        all(fragment in error for fragment in fragments)
        for error in result.errors
    )


def _case_errors(result: BuildResult, case_name: str) -> tuple[str, ...]:
    filename = _module_path(BEHAVIOR_CASES[case_name][0]).name
    return tuple(error for error in result.errors if filename in error)
