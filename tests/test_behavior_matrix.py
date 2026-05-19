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
from sage_mypy_category_plugin.projection import ProviderProjection
from tests.manifest_helpers import external_runtime_class_records_for_test_manifest

type SourceTree = dict[str, "SourceTree"]

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "invariant_core"
REAL_CATEGORIES_ROOT = REPO_ROOT / "tests" / "real_categories"
FINITE_SMALL_GROUPS_VALID = "tests.real_categories.finite_small_groups_valid"
FINITE_SMALL_GROUPS_INVALID = "tests.real_categories.finite_small_groups_invalid"
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
AXIOM_ROOT_CATEGORY = "tests.fixtures.invariant_core.axioms.AxiomRootCategory.Finite"
AXIOM_BEHAVIOR_CASES = {
    "axiom_valid": (
        "tests.fixtures.invariant_core.axiom_behavior_valid",
        "tests.fixtures.invariant_core.axiom_behavior_valid.ValidAxiomOverrideCategory.Finite",
    ),
    "axiom_invalid": (
        "tests.fixtures.invariant_core.axiom_behavior_invalid",
        "tests.fixtures.invariant_core.axiom_behavior_invalid.InvalidAxiomOverrideCategory.Finite",
    ),
}
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
    "decorated_valid": (
        "tests.fixtures.invariant_core.diamond_behavior_decorated_valid",
        "tests.fixtures.invariant_core.diamond_behavior_decorated_base.DecoratedBaseCategory",
        "tests.fixtures.invariant_core.diamond_behavior_decorated_valid.ValidDecoratedOverrideCategory",
    ),
    "decorated_invalid": (
        "tests.fixtures.invariant_core.diamond_behavior_decorated_invalid",
        "tests.fixtures.invariant_core.diamond_behavior_decorated_base.DecoratedBaseCategory",
        "tests.fixtures.invariant_core.diamond_behavior_decorated_invalid.InvalidDecoratedOverrideCategory",
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
    assert not _case_errors(with_plugin, "decorated_valid")
    assert _case_contains(without_plugin, "decorated_valid", "no base method was found")
    assert _case_contains_fragments(
        with_plugin,
        "decorated_invalid",
        "decorated_property",
        "[override]",
    )
    assert _case_contains_fragments(
        with_plugin,
        "decorated_invalid",
        "decorated_classmethod",
        "[override]",
    )
    assert _case_contains_fragments(
        with_plugin,
        "decorated_invalid",
        "decorated_staticmethod",
        "[override]",
    )
    assert _case_contains_fragments(
        with_plugin,
        "decorated_invalid",
        "decorated_abstract",
        "[override]",
    )
    assert _case_contains_fragments(
        with_plugin,
        "decorated_invalid",
        "decorated_overload",
        "[override]",
    )
    assert _case_contains(
        without_plugin,
        "decorated_invalid",
        "no base method was found",
    )


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


def test_local_axiom_behavior_matrix_uses_standard_mypy_rules(
    tmp_path: Path,
) -> None:
    visible_sage_stubs = _write_visible_sage_axiom_stubs(tmp_path)
    config_path = _write_axiom_plugin_config(
        tmp_path,
        visible_sage_stubs=visible_sage_stubs,
    )
    modules = tuple(case[0] for case in AXIOM_BEHAVIOR_CASES.values())

    with_plugin = _run_mypy(
        modules,
        config_path,
        tmp_path,
        mypy_path_entries=(REPO_ROOT, visible_sage_stubs),
    )
    without_plugin = _run_mypy_without_plugin(
        modules,
        tmp_path,
        mypy_path_entries=(REPO_ROOT, visible_sage_stubs),
    )

    assert not _case_errors(with_plugin, "axiom_valid")
    assert _case_contains(without_plugin, "axiom_valid", "no base method was found")
    assert _case_contains(with_plugin, "axiom_invalid", "no base method was found")
    assert _case_contains(without_plugin, "axiom_invalid", "no base method was found")


def test_packages_config_behavior_matrix_end_to_end(tmp_path: Path) -> None:
    """Phase 7 E4: packages= config triggers plugin-owned generation; 4-cell conjunction holds.

    This proves the production path (no pre-generated manifest, no external
    MYPYPATH) produces the same behavioral invariant as the debug manifest= path:

      plugin off + valid code   → "no base method was found" (Sage provider invisible)
      plugin on  + valid code   → no errors (plugin projects provider MRO)
      plugin off + invalid code → "no base method was found"
      plugin on  + invalid code → "no base method was found" (mypy still enforces @override)

    The manifest and stubs are generated by the plugin during the mypy build
    (plugin.__init__) with no external wrapper or MYPYPATH needed.
    """
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    # In production, users configure the packages containing their Sage category
    # definitions.  ValidOverrideCategory / InvalidOverrideCategory ARE Sage
    # categories (they subclass BottomCategory, which is a real Sage Category),
    # so they must be included in the packages scan — exactly as they would be
    # in a real consumer category_specs package.
    valid_module = BEHAVIOR_CASES["valid"][0]
    invalid_module = BEHAVIOR_CASES["invalid"][0]
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                "packages =",
                "    tests.fixtures.invariant_core.diamond_runtime",
                f"    {valid_module}",
                f"    {invalid_module}",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )

    modules = (BEHAVIOR_CASES["valid"][0], BEHAVIOR_CASES["invalid"][0])

    with_plugin = _run_mypy(modules, config_path, tmp_path)
    without_plugin = _run_mypy_without_plugin(modules, tmp_path)

    # Manifest was auto-generated by the plugin during the mypy build
    assert (cache_dir / "projection-manifest.json").is_file()

    # 4-cell behavioral conjunction: provider MROs projected ↔ mypy sees inherited methods
    assert not _case_errors(with_plugin, "valid"), (
        f"Expected no errors for valid code with plugin; got: {_case_errors(with_plugin, 'valid')}"
    )
    assert _case_contains(without_plugin, "valid", "no base method was found"), (
        "Expected valid code to fail without plugin (Sage provider MRO invisible)"
    )
    assert _case_contains(with_plugin, "invalid", "no base method was found"), (
        "Expected invalid @override to still fail with plugin on"
    )
    assert _case_contains(without_plugin, "invalid", "no base method was found")


def test_real_sage_category_behavior_matrix_uses_standard_mypy_rules(
    tmp_path: Path,
) -> None:
    """Phase 3 P3: real mathematical Sage categories satisfy the 4-cell behavioral conjunction.

    Uses real Sage categories (FiniteGroupsOfOrderLessThanTwenty subclassing
    Groups().Finite()) — not synthetic LocalCategoryBase fixtures.  This proves
    the plugin correctly projects real Sage runtime provider MROs, not just the
    synthetic diamond graph.

    The stub_root is pre-declared in mypy_path before build() so that the Sage
    system provider stubs (generated during plugin.__init__) are visible when
    mypy resolves the provider TypeInfos.

      plugin off + valid code   → "no base method was found" (real Sage provider invisible)
      plugin on  + valid code   → no errors (plugin projects runtime provider MRO)
      plugin off + invalid code → "no base method was found"
      plugin on  + invalid code → "no base method was found" (mypy still enforces @override)
    """
    cache_dir = tmp_path / "sage-category-cache"
    # The stub root must be declared in mypy_path BEFORE build() is called so
    # that mypy can see the Sage system provider stubs that the plugin generates
    # during plugin.__init__.  For local Python source files the stub root is
    # not needed (they are found via REPO_ROOT), but Sage system providers
    # (FiniteGroups.ParentMethods, Groups.ParentMethods, etc.) only exist in the
    # generated stubs, so mypy must know the stub root upfront.
    stub_root = cache_dir / "stubs"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.real_categories",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )

    valid_path = REAL_CATEGORIES_ROOT / "finite_small_groups_valid.py"
    invalid_path = REAL_CATEGORIES_ROOT / "finite_small_groups_invalid.py"
    sources = (
        BuildSource(str(valid_path), FINITE_SMALL_GROUPS_VALID, None),
        BuildSource(str(invalid_path), FINITE_SMALL_GROUPS_INVALID, None),
    )

    with_plugin = _run_mypy_with_sources(
        sources,
        config_path,
        tmp_path,
        mypy_path_entries=(stub_root, REPO_ROOT),
    )
    without_plugin = _run_mypy_without_plugin_with_sources(
        sources,
        tmp_path,
    )

    valid_filename = valid_path.name  # "finite_small_groups_valid.py"
    invalid_filename = invalid_path.name  # "finite_small_groups_invalid.py"
    valid_errors = tuple(e for e in with_plugin.errors if valid_filename in e)
    invalid_errors_on = tuple(e for e in with_plugin.errors if invalid_filename in e)
    valid_errors_off = tuple(e for e in without_plugin.errors if valid_filename in e)
    invalid_errors_off = tuple(e for e in without_plugin.errors if invalid_filename in e)

    assert not valid_errors, (
        f"Expected no errors for valid code with plugin; got: {valid_errors}"
    )
    assert any("no base method was found" in e for e in valid_errors_off), (
        "Expected valid code to fail without plugin (real Sage provider MRO invisible)"
    )
    assert any("no base method was found" in e for e in invalid_errors_on), (
        "Expected invalid @override to still fail with plugin on"
    )
    assert any("no base method was found" in e for e in invalid_errors_off)


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
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            tuple(projections.values()),
        ),
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


def _write_axiom_plugin_config(
    tmp_path: Path,
    *,
    visible_sage_stubs: Path,
) -> Path:
    category_fullnames = [
        AXIOM_ROOT_CATEGORY,
        *(case[1] for case in AXIOM_BEHAVIOR_CASES.values()),
    ]
    projections = provider_projections_for_categories(
        tuple(category_fullnames),
        roles=("parent",),
    )
    source_modules = (
        _source_module_record(
            "tests.fixtures.invariant_core.axioms",
            FIXTURE_ROOT / "axioms.py",
        ),
        *(
            _source_module_record(case[0], _module_path(case[0]))
            for case in AXIOM_BEHAVIOR_CASES.values()
        ),
        _source_module_record(
            "sage.categories.finite_sets",
            visible_sage_stubs / "sage" / "categories" / "finite_sets.pyi",
        ),
        _source_module_record(
            "sage.categories.sets_cat",
            visible_sage_stubs / "sage" / "categories" / "sets_cat.pyi",
        ),
        _source_module_record(
            "sage.categories.sets_with_partial_maps",
            visible_sage_stubs
            / "sage"
            / "categories"
            / "sets_with_partial_maps.pyi",
        ),
        _source_module_record(
            "sage.categories.objects",
            visible_sage_stubs / "sage" / "categories" / "objects.pyi",
        ),
    )
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            tuple(projections.values()),
            source_modules=source_modules,
        ),
        source_modules=source_modules,
    )
    manifest_path = tmp_path / "sage-category-axiom-behavior-projections.json"
    config_path = tmp_path / "axiom-behavior-mypy.ini"
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
    source_modules = _write_nested_provider_sources(
        source_root,
        projections=tuple(projections.values()),
    )
    config_path = tmp_path / "nested-provider-mypy.ini"
    manifest_path = tmp_path / "nested-provider-manifest.json"
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            tuple(projections.values()),
            source_modules=source_modules,
        ),
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
    projections: tuple[ProviderProjection, ...],
) -> tuple[SourceModuleRecord, ...]:
    module_trees: dict[str, SourceTree] = defaultdict(dict)
    for fullname in _projection_fullnames(projections):
        if fullname == "builtins.object":
            continue
        module_name, qualname = _importable_module_and_qualname(fullname)
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
        source_bytes = path.read_bytes()
        source_stat = path.stat()
        source_modules.append(
            SourceModuleRecord(
                module=module_name,
                path=str(path),
                sha256=sha256(source_bytes).hexdigest(),
                mtime_ns=source_stat.st_mtime_ns,
            )
        )
    return tuple(source_modules)


def _projection_fullnames(
    projections: tuple[ProviderProjection, ...],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            fullname
            for projection in projections
            for fullname in (
                projection.provider,
                projection.runtime_class,
                *projection.runtime_bases,
                *projection.runtime_mro,
                *projection.provider_bases,
                *projection.provider_mro,
                *projection.unprojected_runtime_mro,
            )
        )
    )


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
    options.enable_error_code = ["explicit-override"]
    options.mypy_path = [str(REPO_ROOT)]
    options.ignore_missing_imports = True
    return options


def _source(module: str) -> BuildSource:
    return BuildSource(str(_module_path(module)), module, None)


def _module_path(module: str) -> Path:
    filename = module.rsplit(".", maxsplit=1)[-1] + ".py"
    return FIXTURE_ROOT / filename


def _run_mypy_with_sources(
    sources: tuple[BuildSource, ...],
    config_path: Path,
    tmp_path: Path,
    *,
    mypy_path_entries: tuple[Path, ...] = (REPO_ROOT,),
) -> BuildResult:
    """Like _run_mypy but accepts explicit BuildSource objects instead of module names.

    Used for categories outside FIXTURE_ROOT (e.g. tests/real_categories/).
    """
    options = _options(tmp_path)
    options.config_file = str(config_path)
    options.plugins = ["sage_mypy_category_plugin.plugin"]
    options.mypy_path = [str(path) for path in mypy_path_entries]
    return build(sources=list(sources), options=options)


def _run_mypy_without_plugin_with_sources(
    sources: tuple[BuildSource, ...],
    tmp_path: Path,
    *,
    mypy_path_entries: tuple[Path, ...] = (REPO_ROOT,),
) -> BuildResult:
    """Like _run_mypy_without_plugin but accepts explicit BuildSource objects."""
    options = _options(tmp_path)
    options.mypy_path = [str(path) for path in mypy_path_entries]
    return build(sources=list(sources), options=options)


def _write_visible_sage_axiom_stubs(tmp_path: Path) -> Path:
    stub_root = tmp_path / "visible-sage-axiom-stubs"
    categories = stub_root / "sage" / "categories"
    categories.mkdir(parents=True)
    (stub_root / "sage" / "__init__.pyi").write_text("")
    (categories / "__init__.pyi").write_text("")
    (categories / "finite_sets.pyi").write_text(
        "\n".join(
            (
                "class FiniteSets:",
                "    class ParentMethods: ...",
                "",
            )
        )
    )
    (categories / "sets_cat.pyi").write_text(
        "\n".join(
            (
                "class Sets:",
                "    class ParentMethods: ...",
                "",
            )
        )
    )
    (categories / "sets_with_partial_maps.pyi").write_text(
        "\n".join(
            (
                "class SetsWithPartialMaps:",
                "    class ParentMethods: ...",
                "",
            )
        )
    )
    (categories / "objects.pyi").write_text(
        "\n".join(
            (
                "class Objects:",
                "    class ParentMethods: ...",
                "",
            )
        )
    )
    return stub_root


def _source_module_record(module_name: str, path: Path) -> SourceModuleRecord:
    source_bytes = path.read_bytes()
    source_stat = path.stat()
    return SourceModuleRecord(
        module=module_name,
        path=str(path),
        sha256=sha256(source_bytes).hexdigest(),
        mtime_ns=source_stat.st_mtime_ns,
    )


def _case_contains(result: BuildResult, case_name: str, fragment: str) -> bool:
    return any(fragment in error for error in _case_errors(result, case_name))


def _case_contains_fragments(
    result: BuildResult,
    case_name: str,
    *fragments: str,
) -> bool:
    return any(
        all(fragment in error for fragment in fragments)
        for error in _case_errors(result, case_name)
    )


def _contains_error(result: BuildResult, fragment: str) -> bool:
    return any(fragment in error for error in result.errors)


def _contains_error_fragments(result: BuildResult, *fragments: str) -> bool:
    return any(
        all(fragment in error for fragment in fragments)
        for error in result.errors
    )


def _case_errors(result: BuildResult, case_name: str) -> tuple[str, ...]:
    filename = _module_path(_behavior_case_module(case_name)).name
    return tuple(error for error in result.errors if filename in error)


def _behavior_case_module(case_name: str) -> str:
    if case_name in BEHAVIOR_CASES:
        return BEHAVIOR_CASES[case_name][0]
    assert case_name in AXIOM_BEHAVIOR_CASES, f"Unknown behavior case {case_name!r}"
    return AXIOM_BEHAVIOR_CASES[case_name][0]
