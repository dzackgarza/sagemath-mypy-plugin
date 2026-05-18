"""TDD tests for plugin correctness on local-wrapper namespaces (the category_specs pattern).

Each test asserts a conjunction over the combinations of (plugin on/off) × (valid/invalid usage)
that fully characterise one behavioral surface. All conjuncts must hold simultaneously.
Tests fail until the plugin is fixed for local-wrapper namespaces.

Surfaces covered:

    ParentMethods @override    — test_plugin_parentmethods_override_correctness
    ElementMethods @override   — test_plugin_elementmethods_override_correctness
    SubcategoryMethods @override  — test_plugin_subcategorymethods_override_correctness
    MorphismMethods @override  — test_plugin_morphismmethods_override_correctness
    Helper-alias @override     — test_plugin_helper_alias_override_correctness
    Construction extra-super @override — test_plugin_construction_extra_super_correctness
    Cross-module construction alias provider — test_plugin_cross_module_construction_alias_provider_correctness
    @final method binding      — test_plugin_final_method_binding_correctness
    @abstractmethod binding    — test_plugin_abstract_method_binding_correctness
    cached_method decorator    — test_plugin_cached_method_decorator_correctness
    Constructors zero-arg      — test_plugin_constructors_zero_arg_correctness
    FunctorialConstruction zero-arg — test_plugin_functorial_construction_zero_arg_correctness
    Construction selector class attribute — test_plugin_construction_selector_class_attribute_correctness
    __classcall_private__ kwargs   — test_plugin_classcall_private_kwargs_correctness
    Operator surfaces          — test_plugin_operator_surfaces_correctness
    Covariant return narrowing — test_plugin_covariant_return_narrowing_correctness
    Transitive covariant return narrowing — test_plugin_transitive_covariant_return_narrowing_correctness
    Value-dependent completion self return — test_plugin_value_dependent_completion_self_return_correctness
    _with_axiom attribute      — test_plugin_with_axiom_correctness
    Method-container receiver self surfaces — test_plugin_receiver_self_surface_correctness
    Runtime receiver inherited methods — test_plugin_runtime_receiver_inherited_method_chain_correctness
    Method-container receiver runtime bases — test_plugin_receiver_runtime_base_correctness
    SubcategoryMethods base_category receiver — test_plugin_subcategory_base_category_receiver_correctness
    Aliased receiver self surfaces — test_plugin_alias_receiver_self_surface_correctness
    Exact module import under suffix collision — test_plugin_exact_module_collision_correctness
    Static axiom base receiver self surfaces — test_plugin_static_axiom_base_receiver_self_correctness
    Static axiom SubcategoryMethods receiver self surfaces — test_plugin_static_axiom_subcategory_receiver_self_correctness
    Static construction extra-super receiver self surfaces — test_plugin_static_construction_extra_super_receiver_self_correctness
    Python-base construction method containers — test_plugin_python_base_construction_method_container_correctness
    Static construction selectors avoid runtime import — test_plugin_static_construction_selector_no_runtime_import_correctness
    Runtime construction selector import failures stay diagnostic — test_plugin_runtime_construction_selector_import_failure_correctness
    Runtime Sage cartesian-product supercategory containers — test_plugin_runtime_cartesian_product_super_category_correctness
    Runtime projection plus Python-base method containers — test_plugin_runtime_projection_with_python_base_provider_correctness
    Recursive axiom bases under runtime projection — test_plugin_recursive_axiom_quotient_projection_correctness
    Runtime Sage enumerated supercategory containers — test_plugin_runtime_enumerated_super_category_correctness
    Runtime Sage facade supercategory containers — test_plugin_runtime_facade_super_category_correctness
    Runtime Sage metric supercategory containers — test_plugin_runtime_metric_super_category_correctness
    Runtime Sage supercategory assigned providers — test_plugin_runtime_super_category_alias_provider_correctness
    Sage category interop stubs — test_sage_category_interop_stub_correctness
    Parent.Hom category keyword — test_plugin_parent_hom_category_keyword_correctness
    Aliased provider type aliases — test_plugin_alias_provider_type_alias_correctness
    Cross-module aliased provider type aliases — test_plugin_cross_module_alias_provider_type_alias_correctness
    Covariant container assignment — test_plugin_covariant_assignment_correctness
    Relative-import axiom base categories — test_plugin_relative_import_axiom_base_correctness
"""
from __future__ import annotations

from functools import cache
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_LOCAL_WRAPPER_FIXTURES = (
    _FIXTURES_DIR / "local_wrapper_pkg" / "category_specs_like" / "mypy_test_fixtures"
)
_CONFIG_WITH_PLUGIN = Path(__file__).resolve().parent / "mypy_test.ini"
_CONFIG_WITHOUT_PLUGIN = Path(__file__).resolve().parent / "mypy_no_plugin.ini"
_FIXTURE_FILES = tuple(sorted(_LOCAL_WRAPPER_FIXTURES.rglob("test_*.py")))
_FIXTURE_BY_NAME = {path.stem: path for path in _FIXTURE_FILES}
_FATAL_MYPY_MARKERS = (
    "INTERNAL ERROR",
    "Traceback",
    "Segmentation fault",
    "Unhandled SIGSEGV",
)


@cache
def _run_local_wrapper_fixture_set(config: Path) -> str:
    from mypy import api

    stdout, _stderr, code = api.run([
        "--config-file", str(config),
        "--no-incremental",
        *(str(path) for path in _FIXTURE_FILES),
    ])
    if any(marker in stdout for marker in _FATAL_MYPY_MARKERS):
        raise AssertionError(stdout)
    if code not in (0, 1):
        raise AssertionError(stdout)
    return stdout


def _diagnostics_for_fixture(stdout: str, path: Path) -> str:
    rel_path = path.relative_to(_PROJECT_ROOT)
    prefixes = (f"{path}:", f"{rel_path}:")
    lines = [line for line in stdout.splitlines() if line.startswith(prefixes)]
    return "\n".join(lines)


def _run(fixture_name: str, config: Path) -> tuple[int, str]:
    path = _FIXTURE_BY_NAME[fixture_name]
    diagnostics = _diagnostics_for_fixture(
        _run_local_wrapper_fixture_set(config),
        path,
    )
    return (1 if diagnostics else 0), diagnostics


def _assert_override_conjunction(valid_fixture: str, invalid_fixture: str) -> None:
    """Assert all four (plugin × validity) cases simultaneously for an override surface."""
    plugin_valid_code,      plugin_valid_out      = _run(valid_fixture,   _CONFIG_WITH_PLUGIN)
    plugin_invalid_code,    plugin_invalid_out    = _run(invalid_fixture, _CONFIG_WITH_PLUGIN)
    noplugin_valid_code,    noplugin_valid_out    = _run(valid_fixture,   _CONFIG_WITHOUT_PLUGIN)
    noplugin_invalid_code,  noplugin_invalid_out  = _run(invalid_fixture, _CONFIG_WITHOUT_PLUGIN)

    errors = []

    if plugin_valid_code != 0:
        errors.append(f"plugin=on  valid  : expected exit 0\n{plugin_valid_out}")

    if plugin_invalid_code == 0:
        errors.append("plugin=on  invalid: expected nonzero exit, got 0")
    elif "no base method was found" not in plugin_invalid_out:
        errors.append(f"plugin=on  invalid: expected 'no base method was found'\n{plugin_invalid_out}")

    if noplugin_valid_code == 0:
        errors.append("plugin=off valid  : expected nonzero exit without plugin, got 0")
    elif "no base method was found" not in noplugin_valid_out:
        errors.append(f"plugin=off valid  : expected 'no base method was found'\n{noplugin_valid_out}")

    if noplugin_invalid_code == 0:
        errors.append("plugin=off invalid: expected nonzero exit without plugin, got 0")
    elif "no base method was found" not in noplugin_invalid_out:
        errors.append(f"plugin=off invalid: expected 'no base method was found'\n{noplugin_invalid_out}")

    assert not errors, "\n\n".join(errors)


def _assert_clean_conjunction(fixture: str, error_code: str) -> None:
    """Assert that a fixture is clean with the plugin and produces `error_code` without it."""
    plugin_code,   plugin_out   = _run(fixture, _CONFIG_WITH_PLUGIN)
    noplugin_code, noplugin_out = _run(fixture, _CONFIG_WITHOUT_PLUGIN)

    errors = []

    if plugin_code != 0:
        errors.append(f"plugin=on : expected exit 0\n{plugin_out}")

    if noplugin_code == 0:
        errors.append("plugin=off: expected nonzero exit without plugin, got 0")
    elif error_code not in noplugin_out:
        errors.append(f"plugin=off: expected '{error_code}'\n{noplugin_out}")

    assert not errors, "\n\n".join(errors)


def _assert_clean_with_and_without_plugin(fixture: str) -> None:
    """Assert that a fixture is clean independent of plugin activation."""
    plugin_code,   plugin_out   = _run(fixture, _CONFIG_WITH_PLUGIN)
    noplugin_code, noplugin_out = _run(fixture, _CONFIG_WITHOUT_PLUGIN)

    errors = []

    if plugin_code != 0:
        errors.append(f"plugin=on : expected exit 0\n{plugin_out}")

    if noplugin_code != 0:
        errors.append(f"plugin=off: expected exit 0\n{noplugin_out}")

    assert not errors, "\n\n".join(errors)


def _assert_error_with_and_without_plugin(fixture: str, error_code: str) -> None:
    """Assert that the plugin does not hide a non-Sage-owned mypy error."""
    plugin_code,   plugin_out   = _run(fixture, _CONFIG_WITH_PLUGIN)
    noplugin_code, noplugin_out = _run(fixture, _CONFIG_WITHOUT_PLUGIN)

    errors = []

    if plugin_code == 0:
        errors.append("plugin=on : expected nonzero exit, got 0")
    elif error_code not in plugin_out:
        errors.append(f"plugin=on : expected '{error_code}'\n{plugin_out}")

    if noplugin_code == 0:
        errors.append("plugin=off: expected nonzero exit, got 0")
    elif error_code not in noplugin_out:
        errors.append(f"plugin=off: expected '{error_code}'\n{noplugin_out}")

    assert not errors, "\n\n".join(errors)


def test_plugin_cached_method_decorator_correctness() -> None:
    """@cached_method stays typed through the bundled Sage stub."""
    _assert_clean_with_and_without_plugin("test_cached_method_decorator")


def test_plugin_does_not_suppress_untyped_method_container_decorators() -> None:
    """An arbitrary untyped decorator is not a Sage category plugin surface."""
    _assert_error_with_and_without_plugin(
        "test_untyped_method_container_decorator",
        "[untyped-decorator]",
    )


def test_plugin_constructors_zero_arg_correctness() -> None:
    """Constructors() zero-arg call must not produce [call-arg]."""
    _assert_clean_conjunction("test_constructors_zero_arg", "[call-arg]")


def test_plugin_functorial_construction_zero_arg_correctness() -> None:
    """FunctorialConstructionCategory zero-arg call must not produce [call-arg]."""
    _assert_clean_conjunction("test_functorial_construction_zero_arg", "[call-arg]")


def test_plugin_construction_selector_class_attribute_correctness() -> None:
    """Construction class attributes must type as zero-arg category selectors."""
    _assert_clean_conjunction("test_construction_selector_class_attribute", "[call-arg]")


def test_plugin_classcall_private_kwargs_correctness() -> None:
    """__classcall_private__ kwargs (e.g. dispatch=False) must not produce [call-arg]."""
    _assert_clean_conjunction("test_classcall_private_kwargs", "[call-arg]")


def test_plugin_does_not_rewrite_non_sage_category_constructors() -> None:
    """Ordinary *Category classes remain subject to normal constructor checking."""
    _assert_error_with_and_without_plugin(
        "test_non_sage_category_constructor",
        "[call-arg]",
    )


def test_plugin_operator_surfaces_correctness() -> None:
    """SubcategoryMethods.__contains__ and ElementMethods.__ne__ must not fire [operator]."""
    _assert_clean_conjunction("test_morphism_methods_callable", "[operator]")


def test_plugin_covariant_return_narrowing_correctness() -> None:
    """Covariant ParentMethods return narrowing must not produce [return-value]."""
    _assert_clean_conjunction("test_covariant_return_narrowing", "[return-value]")


def test_plugin_transitive_covariant_return_narrowing_correctness() -> None:
    """Transitive semantic ParentMethods bases must support covariant returns."""
    _assert_clean_conjunction("test_transitive_covariant_return_narrowing", "[return-value]")


def test_plugin_value_dependent_completion_self_return_correctness() -> None:
    """Ideal-dependent completion may return self under a stronger result category."""
    _assert_clean_conjunction("test_value_dependent_completion_self_return", "[return-value]")


def test_plugin_parentmethods_override_correctness() -> None:
    """ParentMethods @override: plugin on + valid → exit 0; all other cases → error."""
    _assert_override_conjunction("test_valid_override", "test_invalid_override")


def test_plugin_elementmethods_override_correctness() -> None:
    """ElementMethods @override: plugin on + valid → exit 0; all other cases → error."""
    _assert_override_conjunction("test_valid_element_methods_override", "test_invalid_override")


def test_plugin_subcategorymethods_override_correctness() -> None:
    """SubcategoryMethods @override: plugin on + valid → exit 0; all other cases → error."""
    _assert_override_conjunction("test_subcategory_methods_override", "test_invalid_override")


def test_plugin_morphismmethods_override_correctness() -> None:
    """MorphismMethods @override: plugin on + valid → exit 0; all other cases → error."""
    _assert_override_conjunction("test_morphism_methods_override", "test_invalid_override")


def test_plugin_helper_alias_override_correctness() -> None:
    """Helper-alias @override: ParentMethods assigned to helper class; @override resolves through alias."""
    _assert_override_conjunction("test_helper_alias_override", "test_helper_alias_invalid_override")


def test_plugin_construction_extra_super_correctness() -> None:
    """Construction extra-super method containers resolve through Sage's runtime hierarchy."""
    _assert_override_conjunction(
        "test_construction_extra_super_category_methods",
        "test_invalid_override",
    )


def test_plugin_cross_module_construction_alias_provider_correctness() -> None:
    """Construction extra-super bases may be imported ParentMethods aliases."""
    _assert_clean_conjunction(
        "test_cross_module_construction_alias_provider",
        "[attr-defined]",
    )


def test_plugin_final_method_binding_correctness() -> None:
    """@final on method container assignment: plugin suppresses non-method @final error."""
    _assert_clean_conjunction("test_final_method_binding", "[misc]")


def test_plugin_abstract_method_binding_correctness() -> None:
    """@abstractmethod on method container assignment: plugin suppresses non-method error."""
    _assert_clean_conjunction("test_abstract_method_binding", "[misc]")


def test_plugin_with_axiom_correctness() -> None:
    """SubcategoryMethods._with_axiom: plugin on → exit 0; plugin off → [attr-defined]."""
    _assert_clean_conjunction("test_with_axiom", "[attr-defined]")


def test_plugin_receiver_self_surface_correctness() -> None:
    """Method-container self may use receiver methods declared on its category."""
    _assert_clean_conjunction(
        "test_method_container_receiver_self_surface",
        "[attr-defined]",
    )


def test_plugin_runtime_receiver_inherited_method_chain_correctness() -> None:
    """Method-container self may use inherited receiver methods from runtime bases."""
    _assert_clean_conjunction(
        "test_runtime_receiver_inherited_method_chain",
        "[attr-defined]",
    )


def test_plugin_receiver_runtime_base_correctness() -> None:
    """Method-container receiver aliases are valid Sage receiver base objects."""
    _assert_clean_conjunction(
        "test_method_container_receiver_runtime_bases",
        "[arg-type]",
    )


def test_plugin_subcategory_base_category_receiver_correctness() -> None:
    """SubcategoryMethods self exposes Sage's base_category receiver method."""
    _assert_clean_conjunction(
        "test_subcategory_base_category_receiver_self",
        "[attr-defined]",
    )


def test_plugin_alias_receiver_self_surface_correctness() -> None:
    """Aliased ParentMethods providers may use receiver methods declared on their category."""
    _assert_clean_conjunction("test_alias_receiver_self_surface", "[attr-defined]")


def test_plugin_exact_module_collision_correctness() -> None:
    """Exact local-wrapper modules must win over importable shorter suffixes."""
    _assert_override_conjunction(
        "test_exact_module_collision_override",
        "test_invalid_override",
    )


def test_plugin_static_axiom_base_receiver_self_correctness() -> None:
    """Axiom metadata supplies semantic bases when runtime projection is unavailable."""
    _assert_override_conjunction(
        "test_static_axiom_base_receiver_self",
        "test_invalid_override",
    )


def test_plugin_relative_import_axiom_base_correctness() -> None:
    """Axiom metadata may name a category imported from a parent package."""
    _assert_override_conjunction(
        "test_relative_axiom_over_pid",
        "test_invalid_override",
    )


def test_plugin_static_axiom_subcategory_receiver_self_correctness() -> None:
    """SubcategoryMethods receiver methods may come from an axiom base category."""
    _assert_clean_conjunction(
        "test_static_axiom_subcategory_receiver_self",
        "[attr-defined]",
    )


def test_plugin_static_construction_extra_super_receiver_self_correctness() -> None:
    """Construction owner metadata supplies base-category method containers."""
    _assert_override_conjunction(
        "test_static_construction_extra_super_receiver_self",
        "test_invalid_override",
    )


def test_plugin_python_base_construction_method_container_correctness() -> None:
    """Construction method containers inherit methods from their Python base."""
    _assert_clean_conjunction(
        "test_python_base_construction_method_container",
        "no base method was found",
    )


def test_plugin_static_construction_selector_no_runtime_import_correctness() -> None:
    """Construction selector classification should not execute analyzed modules."""
    _assert_clean_conjunction(
        "test_static_construction_selector_no_runtime_import",
        "[call-arg]",
    )


def test_plugin_runtime_construction_selector_import_failure_correctness() -> None:
    """Runtime classification failures should not become mypy internal errors."""
    _assert_error_with_and_without_plugin(
        "test_runtime_construction_selector_import_failure",
        "[call-arg]",
    )


def test_plugin_runtime_cartesian_product_super_category_correctness() -> None:
    """Nested ParentMethods containers inherit Sage cartesian-product methods."""
    _assert_override_conjunction(
        "test_runtime_cartesian_product_super_category",
        "test_invalid_override",
    )


def test_plugin_runtime_projection_with_python_base_provider_correctness() -> None:
    """Projected containers must retain methods from Python category bases."""
    _assert_override_conjunction(
        "test_runtime_projection_with_python_base_provider",
        "test_invalid_override",
    )


def test_plugin_recursive_axiom_quotient_projection_correctness() -> None:
    """Projected construction bases may need static axiom bases recursively."""
    _assert_override_conjunction(
        "test_recursive_axiom_quotient_projection",
        "test_invalid_override",
    )


def test_plugin_runtime_enumerated_super_category_correctness() -> None:
    """Nested ParentMethods containers inherit runtime Sage enumerated methods."""
    _assert_override_conjunction(
        "test_runtime_enumerated_super_category",
        "test_invalid_override",
    )


def test_plugin_runtime_facade_super_category_correctness() -> None:
    """Nested ParentMethods containers inherit runtime Sage facade methods."""
    _assert_override_conjunction(
        "test_runtime_facade_super_category",
        "test_invalid_override",
    )


def test_plugin_runtime_metric_super_category_correctness() -> None:
    """Nested ParentMethods containers inherit runtime Sage metric methods."""
    _assert_override_conjunction(
        "test_runtime_metric_super_category",
        "test_invalid_override",
    )


def test_plugin_runtime_super_category_alias_provider_correctness() -> None:
    """Assigned ParentMethods providers inherit runtime Sage supercategory methods."""
    _assert_override_conjunction(
        "test_runtime_super_category_alias_provider",
        "test_invalid_override",
    )


def test_sage_category_interop_stub_correctness() -> None:
    """Bundled Sage category stubs cover consumed category helper APIs."""
    _assert_clean_with_and_without_plugin("test_sage_category_interop_stubs")


def test_plugin_parent_hom_category_keyword_correctness() -> None:
    """Parent.Hom accepts Sage's unbound category keyword call under the plugin."""
    _assert_clean_conjunction("test_parent_hom_category_keyword", "[call-arg]")


def test_plugin_alias_provider_type_alias_correctness() -> None:
    """Type aliases to aliased ParentMethods providers expose provider methods."""
    _assert_clean_conjunction("test_alias_provider_type_alias", "[attr-defined]")


def test_plugin_cross_module_alias_provider_type_alias_correctness() -> None:
    """Type aliases to imported aliased ParentMethods providers expose provider methods."""
    _assert_clean_conjunction(
        "test_cross_module_alias_provider_type_alias",
        "[attr-defined]",
    )


def test_plugin_covariant_assignment_correctness() -> None:
    """Covariant container assignment: plugin on → exit 0; plugin off → [assignment]."""
    _assert_clean_conjunction("test_covariant_container_assignment", "[assignment]")
