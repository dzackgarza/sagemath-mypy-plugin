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
    @final method binding      — test_plugin_final_method_binding_correctness
    @abstractmethod binding    — test_plugin_abstract_method_binding_correctness
    cached_method decorator    — test_plugin_cached_method_decorator_correctness
    Constructors zero-arg      — test_plugin_constructors_zero_arg_correctness
    FunctorialConstruction zero-arg — test_plugin_functorial_construction_zero_arg_correctness
    __classcall_private__ kwargs   — test_plugin_classcall_private_kwargs_correctness
    Operator surfaces          — test_plugin_operator_surfaces_correctness
    Covariant return narrowing — test_plugin_covariant_return_narrowing_correctness
    Transitive covariant return narrowing — test_plugin_transitive_covariant_return_narrowing_correctness
    Value-dependent completion self return — test_plugin_value_dependent_completion_self_return_correctness
    _with_axiom attribute      — test_plugin_with_axiom_correctness
    Covariant container assignment — test_plugin_covariant_assignment_correctness
"""
from __future__ import annotations

import sys
from pathlib import Path

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_LOCAL_WRAPPER_FIXTURES = (
    _FIXTURES_DIR / "local_wrapper_pkg" / "category_specs_like" / "mypy_test_fixtures"
)
_CONFIG_WITH_PLUGIN = Path(__file__).resolve().parent / "mypy_test.ini"
_CONFIG_WITHOUT_PLUGIN = Path(__file__).resolve().parent / "mypy_no_plugin.ini"


def _run(fixture_name: str, config: Path) -> tuple[int, str]:
    import importlib
    from mypy import api

    mod_name = f"local_wrapper_pkg.category_specs_like.mypy_test_fixtures.{fixture_name}"
    sys.modules.pop(mod_name, None)
    try:
        importlib.import_module(mod_name)
    except Exception:
        pass
    path = str(_LOCAL_WRAPPER_FIXTURES / f"{fixture_name}.py")
    stdout, _stderr, code = api.run([
        "--config-file", str(config),
        "--no-incremental",
        path,
    ])
    return code, stdout


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


def test_plugin_cached_method_decorator_correctness() -> None:
    """@cached_method must not make decorated functions untyped ([untyped-decorator])."""
    _assert_clean_conjunction("test_cached_method_decorator", "[untyped-decorator]")


def test_plugin_constructors_zero_arg_correctness() -> None:
    """Constructors() zero-arg call must not produce [call-arg]."""
    _assert_clean_conjunction("test_constructors_zero_arg", "[call-arg]")


def test_plugin_functorial_construction_zero_arg_correctness() -> None:
    """FunctorialConstructionCategory zero-arg call must not produce [call-arg]."""
    _assert_clean_conjunction("test_functorial_construction_zero_arg", "[call-arg]")


def test_plugin_classcall_private_kwargs_correctness() -> None:
    """__classcall_private__ kwargs (e.g. dispatch=False) must not produce [call-arg]."""
    _assert_clean_conjunction("test_classcall_private_kwargs", "[call-arg]")


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


def test_plugin_final_method_binding_correctness() -> None:
    """@final on method container assignment: plugin suppresses non-method @final error."""
    _assert_clean_conjunction("test_final_method_binding", "[misc]")


def test_plugin_abstract_method_binding_correctness() -> None:
    """@abstractmethod on method container assignment: plugin suppresses non-method error."""
    _assert_clean_conjunction("test_abstract_method_binding", "[misc]")


def test_plugin_with_axiom_correctness() -> None:
    """SubcategoryMethods._with_axiom: plugin on → exit 0; plugin off → [attr-defined]."""
    _assert_clean_conjunction("test_with_axiom", "[attr-defined]")


def test_plugin_covariant_assignment_correctness() -> None:
    """Covariant container assignment: plugin on → exit 0; plugin off → [assignment]."""
    _assert_clean_conjunction("test_covariant_container_assignment", "[assignment]")
