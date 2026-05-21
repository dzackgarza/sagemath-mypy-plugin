from __future__ import annotations

import json
from collections.abc import Sequence
from functools import cache
from hashlib import sha256
from importlib import import_module
from pathlib import Path

import pytest
from mypy.build import BuildResult, build
from mypy.errors import CompileError
from mypy.modulefinder import BuildSource
from mypy.nodes import MypyFile, TypeInfo
from mypy.options import Options

from sage_mypy_category_plugin.manifest import (
    ProjectionManifest,
    SourceModuleRecord,
    UnsupportedProviderRecord,
    load_manifest,
    write_manifest,
)
from sage_mypy_category_plugin.oracle import provider_projections_for_categories
from sage_mypy_category_plugin.oracle import unsupported_provider_traces
from sage_mypy_category_plugin.plugin import (
    CONFIG_SECTION,
    SageCategoryProjectionPlugin,
    _normalize_role_name,
    _source_modules_stale_reason,
)
from sage_mypy_category_plugin.projection import ProviderProjection, ProviderRole
from sage_mypy_category_plugin.stubs import write_generated_stub_tree
from tests.manifest_helpers import external_runtime_class_records_for_test_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_MODULE = "tests.fixtures.invariant_core.diamond_runtime"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "invariant_core" / "diamond_runtime.py"
CATEGORY_FULLNAMES = (
    f"{FIXTURE_MODULE}.TopCategory",
    f"{FIXTURE_MODULE}.LeftCategory",
    f"{FIXTURE_MODULE}.RightCategory",
    f"{FIXTURE_MODULE}.BottomCategory",
)
BOTTOM_PROVIDER = f"{FIXTURE_MODULE}.BottomCategory.ParentMethods"
CATEGORY_BEHAVIOR_BASE_MODULE = (
    "tests.fixtures.invariant_core.diamond_behavior_decorated_base"
)
CATEGORY_BEHAVIOR_PROJECTION_MODULE = (
    "tests.fixtures.invariant_core.diamond_behavior_decorated_projection"
)
CATEGORY_BEHAVIOR_BASE_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "invariant_core"
    / "diamond_behavior_decorated_base.py"
)
CATEGORY_BEHAVIOR_PROJECTION_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "invariant_core"
    / "diamond_behavior_decorated_projection.py"
)
CATEGORY_BEHAVIOR_FULLNAMES = (
    f"{CATEGORY_BEHAVIOR_BASE_MODULE}.DecoratedBaseCategory",
    f"{CATEGORY_BEHAVIOR_PROJECTION_MODULE}.DecoratedProjectionCategory",
)
CATEGORY_BEHAVIOR_PROVIDERS = tuple(
    f"{fullname}.ParentMethods" for fullname in CATEGORY_BEHAVIOR_FULLNAMES
)
CATEGORY_SPECS_LIKE_ROOT_MODULE = (
    "tests.fixtures.invariant_core.category_specs_like.rings"
)
CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE = (
    "tests.fixtures.invariant_core.category_specs_like.rings.subcategories.commutative"
)
CATEGORY_SPECS_LIKE_SUBCATEGORY_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "invariant_core"
    / "category_specs_like"
    / "rings"
    / "subcategories"
    / "commutative.py"
)
CATEGORY_SPECS_LIKE_FULLNAMES = (
    f"{CATEGORY_SPECS_LIKE_ROOT_MODULE}.Rings",
    f"{CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE}._CommutativeRings",
)
CATEGORY_SPECS_LIKE_ROOT_PROVIDER = (
    f"{CATEGORY_SPECS_LIKE_ROOT_MODULE}._RingObjectMethods"
)
CATEGORY_SPECS_LIKE_COMMUTATIVE_PROVIDER = (
    f"{CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE}._CommutativeRings.ParentMethods"
)
PROVIDER_ROLES_MODULE = "tests.fixtures.invariant_core.provider_roles.diamond"
PROVIDER_ROLES_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "invariant_core" / "provider_roles" / "diamond.py"
)
PROVIDER_ROLES_FULLNAMES = (
    f"{PROVIDER_ROLES_MODULE}.TopCategory",
    f"{PROVIDER_ROLES_MODULE}.LeftCategory",
    f"{PROVIDER_ROLES_MODULE}.RightCategory",
    f"{PROVIDER_ROLES_MODULE}.BottomCategory",
)
HOMSET_ROLES_MODULE = "tests.fixtures.invariant_core.provider_roles.homsets"
HOMSET_ROLES_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "invariant_core" / "provider_roles" / "homsets.py"
)
HOMSET_ROLES_FULLNAMES = (
    f"{HOMSET_ROLES_MODULE}.BottomCategory",
    f"{HOMSET_ROLES_MODULE}.RefinedSharedHomsetProviderCategory",
)
REFINED_SHARED_HOMSET_PARENT_PROVIDER = (
    f"{HOMSET_ROLES_MODULE}.RefinedSharedHomsetProviderCategory."
    "Homsets.ParentMethods"
)
SHARED_HOMSET_PARENT_PROVIDER = f"{HOMSET_ROLES_MODULE}.SharedHomsetParentMethods"
AXIOM_FIXTURE_MODULE = "tests.fixtures.invariant_core.axioms"
AXIOM_FIXTURE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "invariant_core" / "axioms.py"
)
NESTED_AXIOM_FULLNAMES = (
    f"{AXIOM_FIXTURE_MODULE}.AxiomRootCategory.Finite",
)
NESTED_AXIOM_PROVIDER = f"{NESTED_AXIOM_FULLNAMES[0]}.ParentMethods"
LINKED_AXIOM_ROOT_MODULE = "tests.fixtures.invariant_core.linked_axiom_root"
LINKED_AXIOM_ROOT_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "invariant_core" / "linked_axiom_root.py"
)
LINKED_AXIOM_FINITE_MODULE = "tests.fixtures.invariant_core.linked_axiom_finite"
LINKED_AXIOM_FINITE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "invariant_core" / "linked_axiom_finite.py"
)
LINKED_AXIOM_FULLNAMES = (
    f"{LINKED_AXIOM_ROOT_MODULE}.LinkedAxiomRootCategory.Finite",
)
LINKED_AXIOM_PROVIDER = (
    f"{LINKED_AXIOM_FINITE_MODULE}.LinkedFiniteAxiomCategory.ParentMethods"
)
COMMUTATIVE_RINGS_CATEGORY = "sage.categories.commutative_rings.CommutativeRings"
COMMUTATIVE_RINGS_PROVIDER = (
    "sage.categories.commutative_rings.CommutativeRings.ParentMethods"
)
FUNCTORIAL_CARTESIAN_CATEGORY = (
    "tests.fixtures.invariant_core.functorial.cartesian_products."
    "CartesianProductsCategory"
)
FUNCTORIAL_CARTESIAN_PARENT_PROVIDER = (
    "sage.categories.sets_cat.Sets.CartesianProducts.ParentMethods"
)
FUNCTORIAL_CARTESIAN_ELEMENT_PROVIDER = (
    "sage.categories.sets_cat.Sets.CartesianProducts.ElementMethods"
)
FUNCTORIAL_TENSOR_CATEGORY = (
    "tests.fixtures.invariant_core.functorial.tensor_products."
    "TensorProductsCategory"
)
FUNCTORIAL_TENSOR_PARENT_PROVIDER = (
    "sage.categories.modules.Modules.TensorProducts.ParentMethods"
)
PARAMETERIZED_CATEGORY_FULLNAMES = (
    "tests.fixtures.invariant_core.parameterized.ModulesOverIntegers",
    "tests.fixtures.invariant_core.parameterized.ModulesOverRationals",
    "tests.fixtures.invariant_core.parameterized.VectorSpacesOverRationals",
)
PARAMETERIZED_MODULES_PROVIDER = "sage.categories.modules.Modules.ParentMethods"
PARAMETERIZED_VECTOR_SPACES_PROVIDER = (
    "sage.categories.vector_spaces.VectorSpaces.ParentMethods"
)
DIAMOND_SOURCE_MODULE = SourceModuleRecord(
    module=FIXTURE_MODULE,
    path="tests/fixtures/invariant_core/diamond_runtime.py",
    sha256=sha256(FIXTURE_PATH.read_bytes()).hexdigest(),
    mtime_ns=FIXTURE_PATH.stat().st_mtime_ns,
)


def _provider_projections(
    category_fullnames: tuple[str, ...],
    *,
    roles: tuple[ProviderRole, ...],
) -> dict[str, ProviderProjection]:
    return dict(_provider_projection_items(category_fullnames, roles))


def _provider_projections_with_unsupported(
    category_fullnames: tuple[str, ...],
    *,
    roles: tuple[ProviderRole, ...],
) -> tuple[dict[str, ProviderProjection], tuple[UnsupportedProviderRecord, ...]]:
    projections = provider_projections_for_categories(category_fullnames, roles=roles)
    unsupported_providers = tuple(
        UnsupportedProviderRecord(
            provider=trace.provider,
            role=trace.role,
            reason=trace.reason,
            runtime_classes=trace.runtime_classes,
            runtime_mros=trace.runtime_mros,
        )
        for trace in unsupported_provider_traces()
    )
    return projections, unsupported_providers


@cache
def _provider_projection_items(
    category_fullnames: tuple[str, ...],
    roles: tuple[ProviderRole, ...],
) -> tuple[tuple[str, ProviderProjection], ...]:
    return tuple(
        provider_projections_for_categories(category_fullnames, roles=roles).items()
    )


def test_plugin_projects_structural_typeinfo_mros_from_manifest(
    tmp_path: Path,
) -> None:
    diamond_projections = _provider_projections(
        CATEGORY_FULLNAMES,
        roles=("parent",),
    )
    category_specs_projections = _provider_projections(
        CATEGORY_SPECS_LIKE_FULLNAMES,
        roles=("parent",),
    )
    decorated_behavior_projections = _provider_projections(
        CATEGORY_BEHAVIOR_FULLNAMES,
        roles=("parent",),
    )
    provider_role_projections = _provider_projections(
        PROVIDER_ROLES_FULLNAMES,
        roles=("element", "subcategory", "morphism"),
    )
    homset_projections, homset_unsupported_providers = (
        _provider_projections_with_unsupported(
            HOMSET_ROLES_FULLNAMES,
            roles=("homset_parent", "homset_element"),
        )
    )
    base_path = tmp_path / "base_provider.py"
    consumer_path = tmp_path / "consumer.py"
    base_path.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "",
                "class BaseCategory:",
                "    class ParentMethods:",
                "        def base_method(self) -> int:",
                "            return 1",
                "",
            )
        )
    )
    consumer_path.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "",
                "class ConsumerCategory:",
                "    class ParentMethods:",
                "        def consumer_method(self) -> int:",
                "            return 2",
                "",
            )
        )
    )

    consumer_provider = "consumer.ConsumerCategory.ParentMethods"
    base_provider = "base_provider.BaseCategory.ParentMethods"
    cross_module_projections = {
        base_provider: ProviderProjection(
            provider=base_provider,
            role="parent",
            runtime_class="base_provider.BaseCategory.parent_class",
            runtime_bases=("builtins.object",),
            runtime_mro=(
                "base_provider.BaseCategory.parent_class",
                "builtins.object",
            ),
            provider_bases=(),
            provider_mro=(base_provider,),
        ),
        consumer_provider: ProviderProjection(
            provider=consumer_provider,
            role="parent",
            runtime_class="consumer.ConsumerCategory.parent_class",
            runtime_bases=("base_provider.BaseCategory.parent_class",),
            runtime_mro=(
                "consumer.ConsumerCategory.parent_class",
                "base_provider.BaseCategory.parent_class",
                "builtins.object",
            ),
            provider_bases=(base_provider,),
            provider_mro=(consumer_provider, base_provider),
        ),
    }
    projections = {
        **diamond_projections,
        **category_specs_projections,
        **decorated_behavior_projections,
        **provider_role_projections,
        **homset_projections,
        **cross_module_projections,
    }
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        unsupported_providers=homset_unsupported_providers,
        projections=tuple(projections.values()),
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            tuple(projections.values()),
        ),
    )
    manifest_path = tmp_path / "sage-category-structural-projections.json"
    config_path = tmp_path / "mypy.ini"
    stub_root = tmp_path / "visible-sage-stubs"
    fixture_sources = (
        (FIXTURE_PATH, FIXTURE_MODULE),
        (
            CATEGORY_SPECS_LIKE_SUBCATEGORY_PATH,
            CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE,
        ),
        (CATEGORY_BEHAVIOR_BASE_PATH, CATEGORY_BEHAVIOR_BASE_MODULE),
        (CATEGORY_BEHAVIOR_PROJECTION_PATH, CATEGORY_BEHAVIOR_PROJECTION_MODULE),
        (PROVIDER_ROLES_PATH, PROVIDER_ROLES_MODULE),
        (HOMSET_ROLES_PATH, HOMSET_ROLES_MODULE),
        (consumer_path, "consumer"),
    )
    _write_visible_sage_provider_stubs(stub_root)
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

    result = _build_fixture(
        config_path,
        tmp_path,
        fixture_sources=fixture_sources,
        mypy_path_entries=(REPO_ROOT, tmp_path, stub_root),
    )
    repeated_result = _build_fixture(
        config_path,
        tmp_path,
        fixture_sources=fixture_sources,
        mypy_path_entries=(REPO_ROOT, tmp_path, stub_root),
    )
    result_without_plugin = _build_fixture_without_plugin(
        tmp_path,
        fixture_sources=fixture_sources,
        mypy_path_entries=(REPO_ROOT, tmp_path),
    )

    assert result.errors == []
    assert repeated_result.errors == []
    assert result_without_plugin.errors == []
    bottom_parent_info = _nested_typeinfo(
        result,
        module=FIXTURE_MODULE,
        outer="BottomCategory",
        inner="ParentMethods",
    )
    repeated_bottom_parent_info = _nested_typeinfo(
        repeated_result,
        module=FIXTURE_MODULE,
        outer="BottomCategory",
        inner="ParentMethods",
    )
    baseline_bottom_parent_info = _nested_typeinfo(
        result_without_plugin,
        module=FIXTURE_MODULE,
        outer="BottomCategory",
        inner="ParentMethods",
    )
    assert tuple(info.fullname for info in baseline_bottom_parent_info.mro) == (
        BOTTOM_PROVIDER,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in baseline_bottom_parent_info.bases) == (
        "builtins.object",
    )
    assert tuple(info.fullname for info in bottom_parent_info.mro) == (
        *diamond_projections[BOTTOM_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in bottom_parent_info.bases) == (
        diamond_projections[BOTTOM_PROVIDER].provider_bases
    )
    assert tuple(info.fullname for info in repeated_bottom_parent_info.mro) == (
        *diamond_projections[BOTTOM_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in repeated_bottom_parent_info.bases) == (
        diamond_projections[BOTTOM_PROVIDER].provider_bases
    )

    commutative_parent_info = _nested_typeinfo(
        result,
        module=CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE,
        outer="_CommutativeRings",
        inner="ParentMethods",
    )
    baseline_commutative_parent_info = _nested_typeinfo(
        result_without_plugin,
        module=CATEGORY_SPECS_LIKE_SUBCATEGORY_MODULE,
        outer="_CommutativeRings",
        inner="ParentMethods",
    )
    expected_commutative_mro = category_specs_projections[
        CATEGORY_SPECS_LIKE_COMMUTATIVE_PROVIDER
    ].provider_mro
    root_parent_info = result.files[CATEGORY_SPECS_LIKE_ROOT_MODULE].names[
        "_RingObjectMethods"
    ].node
    assert isinstance(root_parent_info, TypeInfo)
    assert tuple(info.fullname for info in baseline_commutative_parent_info.mro) == (
        CATEGORY_SPECS_LIKE_COMMUTATIVE_PROVIDER,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in baseline_commutative_parent_info.bases) == (
        "builtins.object",
    )
    assert tuple(info.fullname for info in commutative_parent_info.mro) == (
        *expected_commutative_mro,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in commutative_parent_info.bases) == (
        category_specs_projections[CATEGORY_SPECS_LIKE_COMMUTATIVE_PROVIDER].provider_bases
    )
    assert expected_commutative_mro == (
        CATEGORY_SPECS_LIKE_COMMUTATIVE_PROVIDER,
        CATEGORY_SPECS_LIKE_ROOT_PROVIDER,
    )
    assert root_parent_info.fullname == CATEGORY_SPECS_LIKE_ROOT_PROVIDER

    for provider, module, outer in zip(
        CATEGORY_BEHAVIOR_PROVIDERS,
        (
            CATEGORY_BEHAVIOR_BASE_MODULE,
            CATEGORY_BEHAVIOR_PROJECTION_MODULE,
        ),
        (
            "DecoratedBaseCategory",
            "DecoratedProjectionCategory",
        ),
        strict=True,
    ):
        decorated_info = _nested_typeinfo(
            result,
            module=module,
            outer=outer,
            inner="ParentMethods",
        )
        baseline_decorated_info = _nested_typeinfo(
            result_without_plugin,
            module=module,
            outer=outer,
            inner="ParentMethods",
        )

        assert tuple(info.fullname for info in baseline_decorated_info.mro) == (
            provider,
            "builtins.object",
        )
        assert tuple(base.type.fullname for base in baseline_decorated_info.bases) == (
            "builtins.object",
        )
        assert tuple(info.fullname for info in decorated_info.mro) == (
            *decorated_behavior_projections[provider].provider_mro,
            "builtins.object",
        )
        assert tuple(base.type.fullname for base in decorated_info.bases) == (
            decorated_behavior_projections[provider].provider_bases
        )

    for provider_name in ("ElementMethods", "SubcategoryMethods", "MorphismMethods"):
        provider = f"{PROVIDER_ROLES_MODULE}.BottomCategory.{provider_name}"
        role_info = _nested_typeinfo(
            result,
            module=PROVIDER_ROLES_MODULE,
            outer="BottomCategory",
            inner=provider_name,
        )
        baseline_role_info = _nested_typeinfo(
            result_without_plugin,
            module=PROVIDER_ROLES_MODULE,
            outer="BottomCategory",
            inner=provider_name,
        )

        assert tuple(info.fullname for info in baseline_role_info.mro) == (
            provider,
            "builtins.object",
        )
        assert tuple(base.type.fullname for base in baseline_role_info.bases) == (
            "builtins.object",
        )
        assert tuple(info.fullname for info in role_info.mro) == (
            *projections[provider].provider_mro,
            "builtins.object",
        )
        assert tuple(base.type.fullname for base in role_info.bases) == (
            projections[provider].provider_bases
        )

    homsets_info = _nested_typeinfo(
        result,
        module=HOMSET_ROLES_MODULE,
        outer="BottomCategory",
        inner="Homsets",
    )
    parent_provider = f"{HOMSET_ROLES_MODULE}.BottomCategory.Homsets.ParentMethods"
    element_provider = f"{HOMSET_ROLES_MODULE}.BottomCategory.Homsets.ElementMethods"
    parent_info = _inner_typeinfo(homsets_info, "ParentMethods")
    element_info = _inner_typeinfo(homsets_info, "ElementMethods")
    assert tuple(info.fullname for info in parent_info.mro) == (
        *homset_projections[parent_provider].provider_mro,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in parent_info.bases) == (
        homset_projections[parent_provider].provider_bases
    )
    assert tuple(info.fullname for info in element_info.mro) == (
        *homset_projections[element_provider].provider_mro,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in element_info.bases) == (
        homset_projections[element_provider].provider_bases
    )
    refined_homsets_info = _nested_typeinfo(
        result,
        module=HOMSET_ROLES_MODULE,
        outer="RefinedSharedHomsetProviderCategory",
        inner="Homsets",
    )
    baseline_refined_homsets_info = _nested_typeinfo(
        result_without_plugin,
        module=HOMSET_ROLES_MODULE,
        outer="RefinedSharedHomsetProviderCategory",
        inner="Homsets",
    )
    refined_parent_info = _inner_typeinfo(refined_homsets_info, "ParentMethods")
    baseline_refined_parent_info = _inner_typeinfo(
        baseline_refined_homsets_info,
        "ParentMethods",
    )
    refined_homset_mro = homset_projections[
        REFINED_SHARED_HOMSET_PARENT_PROVIDER
    ].provider_mro
    assert tuple(info.fullname for info in baseline_refined_parent_info.mro) == (
        REFINED_SHARED_HOMSET_PARENT_PROVIDER,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in baseline_refined_parent_info.bases) == (
        "builtins.object",
    )
    assert refined_homset_mro == (
        REFINED_SHARED_HOMSET_PARENT_PROVIDER,
        SHARED_HOMSET_PARENT_PROVIDER,
        "sage.categories.objects.Objects.ParentMethods",
    )
    assert tuple(info.fullname for info in refined_parent_info.mro) == (
        *refined_homset_mro,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in refined_parent_info.bases) == (
        homset_projections[REFINED_SHARED_HOMSET_PARENT_PROVIDER].provider_bases
    )

    consumer_info = _nested_typeinfo(
        result,
        module="consumer",
        outer="ConsumerCategory",
        inner="ParentMethods",
    )
    baseline_consumer_info = _nested_typeinfo(
        result_without_plugin,
        module="consumer",
        outer="ConsumerCategory",
        inner="ParentMethods",
    )
    assert "base_provider" in result.files
    assert "base_provider" not in result_without_plugin.files
    assert tuple(info.fullname for info in baseline_consumer_info.mro) == (
        consumer_provider,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in baseline_consumer_info.bases) == (
        "builtins.object",
    )
    assert tuple(info.fullname for info in consumer_info.mro) == (
        consumer_provider,
        base_provider,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in consumer_info.bases) == (
        cross_module_projections[consumer_provider].provider_bases
    )


def test_plugin_projects_nested_axiom_typeinfo_mro_from_manifest(
    tmp_path: Path,
) -> None:
    projections = _provider_projections(
        NESTED_AXIOM_FULLNAMES,
        roles=("parent",),
    )
    stub_root = tmp_path / "visible-sage-stubs"
    source_modules = _write_projected_provider_stubs(
        stub_root,
        projections=tuple(projections.values()),
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
    manifest_path = tmp_path / "sage-category-nested-axiom-projections.json"
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

    result = _build_fixture(
        config_path,
        tmp_path,
        fixture_path=AXIOM_FIXTURE_PATH,
        fixture_module=AXIOM_FIXTURE_MODULE,
        mypy_path_entries=(REPO_ROOT, stub_root),
    )
    result_without_plugin = _build_fixture_without_plugin(
        tmp_path,
        fixture_path=AXIOM_FIXTURE_PATH,
        fixture_module=AXIOM_FIXTURE_MODULE,
        mypy_path_entries=(REPO_ROOT,),
    )

    assert result.errors == []
    assert result_without_plugin.errors == []
    axiom_category_info = result.files[AXIOM_FIXTURE_MODULE].names[
        "AxiomRootCategory"
    ].node
    baseline_axiom_category_info = result_without_plugin.files[
        AXIOM_FIXTURE_MODULE
    ].names["AxiomRootCategory"].node
    assert isinstance(axiom_category_info, TypeInfo)
    assert isinstance(baseline_axiom_category_info, TypeInfo)
    axiom_finite_info = _inner_typeinfo(axiom_category_info, "Finite")
    baseline_axiom_finite_info = _inner_typeinfo(
        baseline_axiom_category_info,
        "Finite",
    )
    axiom_parent_info = _inner_typeinfo(axiom_finite_info, "ParentMethods")
    baseline_axiom_parent_info = _inner_typeinfo(
        baseline_axiom_finite_info,
        "ParentMethods",
    )

    assert tuple(info.fullname for info in baseline_axiom_parent_info.mro) == (
        NESTED_AXIOM_PROVIDER,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in baseline_axiom_parent_info.bases) == (
        "builtins.object",
    )
    assert tuple(info.fullname for info in axiom_parent_info.mro) == (
        *projections[NESTED_AXIOM_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in axiom_parent_info.bases) == (
        projections[NESTED_AXIOM_PROVIDER].provider_bases
    )


def test_plugin_projects_linked_axiom_typeinfo_mro_from_manifest(
    tmp_path: Path,
) -> None:
    projections = _provider_projections(
        LINKED_AXIOM_FULLNAMES,
        roles=("parent",),
    )
    stub_root = tmp_path / "visible-sage-stubs"
    source_modules = _write_projected_provider_stubs(
        stub_root,
        projections=tuple(projections.values()),
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
    manifest_path = tmp_path / "sage-category-linked-axiom-projections.json"
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

    fixture_sources = (
        (LINKED_AXIOM_ROOT_PATH, LINKED_AXIOM_ROOT_MODULE),
        (LINKED_AXIOM_FINITE_PATH, LINKED_AXIOM_FINITE_MODULE),
    )
    result = _build_fixture(
        config_path,
        tmp_path,
        fixture_sources=fixture_sources,
        mypy_path_entries=(REPO_ROOT, stub_root),
    )
    result_without_plugin = _build_fixture_without_plugin(
        tmp_path,
        fixture_sources=fixture_sources,
        mypy_path_entries=(REPO_ROOT,),
    )

    assert result.errors == []
    assert result_without_plugin.errors == []
    linked_info = result.files[LINKED_AXIOM_FINITE_MODULE].names[
        "LinkedFiniteAxiomCategory"
    ].node
    baseline_linked_info = result_without_plugin.files[
        LINKED_AXIOM_FINITE_MODULE
    ].names["LinkedFiniteAxiomCategory"].node
    assert isinstance(linked_info, TypeInfo)
    assert isinstance(baseline_linked_info, TypeInfo)
    linked_parent_info = _inner_typeinfo(linked_info, "ParentMethods")
    baseline_linked_parent_info = _inner_typeinfo(
        baseline_linked_info,
        "ParentMethods",
    )

    assert tuple(info.fullname for info in baseline_linked_parent_info.mro) == (
        LINKED_AXIOM_PROVIDER,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in baseline_linked_parent_info.bases) == (
        "builtins.object",
    )
    assert tuple(info.fullname for info in linked_parent_info.mro) == (
        *projections[LINKED_AXIOM_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in linked_parent_info.bases) == (
        projections[LINKED_AXIOM_PROVIDER].provider_bases
    )


def test_plugin_accepts_sidecar_homset_external_provider_boundary(
    tmp_path: Path,
) -> None:
    projections, unsupported_providers = _provider_projections_with_unsupported(
        HOMSET_ROLES_FULLNAMES,
        roles=("homset_parent", "homset_element"),
    )
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        unsupported_providers=unsupported_providers,
        projections=tuple(projections.values()),
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            tuple(projections.values()),
        ),
    )
    manifest_path = tmp_path / "sage-category-homset-projections.json"
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

    result = _build_fixture(
        config_path,
        tmp_path,
        fixture_path=HOMSET_ROLES_PATH,
        fixture_module=HOMSET_ROLES_MODULE,
    )

    assert result.errors == []


def test_plugin_projects_sage_provider_typeinfo_mros_from_source_modules(
    tmp_path: Path,
) -> None:
    axiom_projections = _provider_projections(
        (COMMUTATIVE_RINGS_CATEGORY,),
        roles=("parent",),
    )
    cartesian_projections = _provider_projections(
        (FUNCTORIAL_CARTESIAN_CATEGORY,),
        roles=("parent", "element"),
    )
    tensor_projections = _provider_projections(
        (FUNCTORIAL_TENSOR_CATEGORY,),
        roles=("parent",),
    )
    parameterized_projections = _provider_projections(
        PARAMETERIZED_CATEGORY_FULLNAMES,
        roles=("parent",),
    )
    projections = {
        **axiom_projections,
        **cartesian_projections,
        **tensor_projections,
        **parameterized_projections,
    }
    manifest_path = tmp_path / "sage-provider-source-modules.json"
    config_path = tmp_path / "mypy.ini"
    stub_root = tmp_path / "visible-sage-stubs"
    source_modules = _write_projected_provider_stubs(
        stub_root,
        projections=tuple(projections.values()),
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
    axiom_fixture_path = tmp_path / "axiom_consumer.py"
    axiom_fixture_path.write_text(
        "\n".join(
            (
                "from sage.categories.commutative_rings import CommutativeRings",
                "CommutativeRings.ParentMethods",
                "",
            )
        )
    )
    cartesian_fixture_path = tmp_path / "cartesian_products_consumer.py"
    cartesian_fixture_path.write_text(
        "\n".join(
            (
                "from sage.categories.sets_cat import Sets",
                "Sets.CartesianProducts.ParentMethods",
                "Sets.CartesianProducts.ElementMethods",
                "",
            )
        )
    )
    tensor_fixture_path = tmp_path / "tensor_products_consumer.py"
    tensor_fixture_path.write_text(
        "\n".join(
            (
                "from sage.categories.modules import Modules",
                "Modules.TensorProducts.ParentMethods",
                "",
            )
        )
    )
    parameterized_fixture_path = tmp_path / "parameterized_consumer.py"
    parameterized_fixture_path.write_text(
        "\n".join(
            (
                "from sage.categories.modules import Modules",
                "from sage.categories.vector_spaces import VectorSpaces",
                "Modules.ParentMethods",
                "VectorSpaces.ParentMethods",
                "",
            )
        )
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

    result = _build_fixture(
        config_path,
        tmp_path,
        fixture_sources=(
            (axiom_fixture_path, "axiom_consumer"),
            (cartesian_fixture_path, "cartesian_products_consumer"),
            (tensor_fixture_path, "tensor_products_consumer"),
            (parameterized_fixture_path, "parameterized_consumer"),
        ),
        mypy_path_entries=(stub_root,),
    )
    commutative_info = _nested_typeinfo(
        result,
        module="sage.categories.commutative_rings",
        outer="CommutativeRings",
        inner="ParentMethods",
    )
    sets_info = result.files["sage.categories.sets_cat"].names["Sets"].node
    assert isinstance(sets_info, TypeInfo)
    cartesian_products_info = _inner_typeinfo(sets_info, "CartesianProducts")
    parent_info = _inner_typeinfo(cartesian_products_info, "ParentMethods")
    element_info = _inner_typeinfo(cartesian_products_info, "ElementMethods")
    modules_info = result.files["sage.categories.modules"].names["Modules"].node
    vector_spaces_info = result.files["sage.categories.vector_spaces"].names[
        "VectorSpaces"
    ].node
    assert isinstance(modules_info, TypeInfo)
    assert isinstance(vector_spaces_info, TypeInfo)
    modules_parent_info = _inner_typeinfo(modules_info, "ParentMethods")
    tensor_products_info = _inner_typeinfo(modules_info, "TensorProducts")
    tensor_parent_info = _inner_typeinfo(tensor_products_info, "ParentMethods")
    vector_spaces_parent_info = _inner_typeinfo(
        vector_spaces_info,
        "ParentMethods",
    )

    assert result.errors == []
    assert tuple(info.fullname for info in commutative_info.mro) == (
        *axiom_projections[COMMUTATIVE_RINGS_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in commutative_info.bases) == (
        axiom_projections[COMMUTATIVE_RINGS_PROVIDER].provider_bases
    )
    assert tuple(info.fullname for info in parent_info.mro) == (
        *cartesian_projections[FUNCTORIAL_CARTESIAN_PARENT_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in parent_info.bases) == (
        cartesian_projections[FUNCTORIAL_CARTESIAN_PARENT_PROVIDER].provider_bases
    )
    assert tuple(info.fullname for info in element_info.mro) == (
        *cartesian_projections[FUNCTORIAL_CARTESIAN_ELEMENT_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in element_info.bases) == (
        cartesian_projections[FUNCTORIAL_CARTESIAN_ELEMENT_PROVIDER].provider_bases
    )
    assert tuple(info.fullname for info in tensor_parent_info.mro) == (
        *tensor_projections[FUNCTORIAL_TENSOR_PARENT_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in tensor_parent_info.bases) == (
        tensor_projections[FUNCTORIAL_TENSOR_PARENT_PROVIDER].provider_bases
    )
    assert tuple(info.fullname for info in modules_parent_info.mro) == (
        *parameterized_projections[PARAMETERIZED_MODULES_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in modules_parent_info.bases) == (
        parameterized_projections[PARAMETERIZED_MODULES_PROVIDER].provider_bases
    )
    assert tuple(info.fullname for info in vector_spaces_parent_info.mro) == (
        *parameterized_projections[PARAMETERIZED_VECTOR_SPACES_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(base.type.fullname for base in vector_spaces_parent_info.bases) == (
        parameterized_projections[PARAMETERIZED_VECTOR_SPACES_PROVIDER].provider_bases
    )


def test_plugin_dependency_modules_use_manifest_source_modules_for_nested_axioms(
    tmp_path: Path,
) -> None:
    projections = _provider_projections(
        (COMMUTATIVE_RINGS_CATEGORY,),
        roles=("parent",),
    )
    stub_root = tmp_path / "visible-sage-stubs"
    source_modules = _write_projected_provider_stubs(
        stub_root,
        projections=tuple(projections.values()),
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
    manifest_path = tmp_path / "sage-category-axiom-projections.json"
    config_path = tmp_path / "mypy.ini"
    write_manifest(manifest_path, manifest)
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )
    mypy_file = MypyFile([], [])
    mypy_file._fullname = "sage.categories.commutative_rings"
    options = Options()
    options.config_file = str(config_path)

    deps = SageCategoryProjectionPlugin(options).get_additional_deps(mypy_file)
    dep_modules = {module for _, module, _ in deps}

    assert "sage.categories.magmas" in dep_modules
    assert "sage.categories.additive_magmas" in dep_modules
    assert "sage.categories.magmas.Magmas" not in dep_modules
    assert "sage.categories.additive_magmas.AdditiveMagmas" not in dep_modules


def test_plugin_fails_strict_projection_for_missing_provider_references(
    tmp_path: Path,
) -> None:
    fixture_path = tmp_path / "strict_missing.py"
    fixture_path.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "",
                "class MissingBaseCategory:",
                "    class ParentMethods:",
                "        def base_field_probe(self) -> int:",
                "            return 1",
                "",
                "class MissingMroCategory:",
                "    class ParentMethods:",
                "        def mro_field_probe(self) -> int:",
                "            return 2",
                "",
            )
        )
    )
    missing_base_provider = "strict_missing.MissingBaseCategory.ParentMethods"
    missing_mro_provider = "strict_missing.MissingMroCategory.ParentMethods"
    missing_provider = "strict_missing.MissingCategory.ParentMethods"
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=(
            ProviderProjection(
                provider=missing_base_provider,
                role="parent",
                runtime_class="strict_missing.MissingBaseCategory.parent_class",
                runtime_bases=("strict_missing.MissingCategory.parent_class",),
                runtime_mro=(
                    "strict_missing.MissingBaseCategory.parent_class",
                    "strict_missing.MissingCategory.parent_class",
                    "builtins.object",
                ),
                provider_bases=(missing_provider,),
                provider_mro=(missing_base_provider, missing_provider),
            ),
            ProviderProjection(
                provider=missing_mro_provider,
                role="parent",
                runtime_class="strict_missing.MissingMroCategory.parent_class",
                runtime_bases=("builtins.object",),
                runtime_mro=(
                    "strict_missing.MissingMroCategory.parent_class",
                    "strict_missing.MissingCategory.parent_class",
                    "builtins.object",
                ),
                provider_bases=(),
                provider_mro=(missing_mro_provider, missing_provider),
            ),
            ProviderProjection(
                provider=missing_provider,
                role="parent",
                runtime_class="strict_missing.MissingCategory.parent_class",
                runtime_bases=("builtins.object",),
                runtime_mro=(
                    "strict_missing.MissingCategory.parent_class",
                    "builtins.object",
                ),
                provider_bases=(),
                provider_mro=(missing_provider,),
            ),
        ),
    )
    manifest_path = tmp_path / "sage-category-projections-missing.json"
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

    result = _build_fixture(
        config_path,
        tmp_path,
        fixture_path=fixture_path,
        fixture_module="strict_missing",
        mypy_path_entries=(tmp_path,),
    )
    missing_base_info = _nested_typeinfo(
        result,
        module="strict_missing",
        outer="MissingBaseCategory",
        inner="ParentMethods",
    )
    missing_mro_info = _nested_typeinfo(
        result,
        module="strict_missing",
        outer="MissingMroCategory",
        inner="ParentMethods",
    )

    assert tuple(info.fullname for info in missing_base_info.mro) == (
        missing_base_provider,
        "builtins.object",
    )
    assert tuple(info.fullname for info in missing_mro_info.mro) == (
        missing_mro_provider,
        "builtins.object",
    )
    assert any(
        missing_base_provider in error and "provider_bases" in error
        for error in result.errors
    )
    assert any(
        missing_mro_provider in error and "provider_mro" in error
        for error in result.errors
    )


def test_plugin_reports_semantic_manifest_config_data(tmp_path: Path) -> None:
    projections = _provider_projections(
        CATEGORY_FULLNAMES,
        roles=("parent",),
    )
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        sage_git_revision="abc123abc123abc123abc123abc123abc123abcd",
        python_version="3.12.13",
        projections=tuple(projections.values()),
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            tuple(projections.values()),
            source_modules=(DIAMOND_SOURCE_MODULE,),
        ),
        source_modules=(DIAMOND_SOURCE_MODULE,),
    )
    manifest_path = tmp_path / "sage-category-projections.json"
    config_path = tmp_path / "mypy.ini"
    write_manifest(manifest_path, manifest)
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )

    options = Options()
    options.config_file = str(config_path)
    plugin = SageCategoryProjectionPlugin(options)
    config_data = plugin.report_config_data(
        ctx=None,  # type: ignore[arg-type]
    )
    # Plugin regenerates stubs on debug_manifest init, refreshing source_modules.
    # Load the on-disk manifest to compare the post-init source_module_digest.
    refreshed_manifest = load_manifest(manifest_path)

    assert config_data["manifest_semantic_projection_digest"] == (
        manifest.semantic_projection_digest
    )
    assert config_data["manifest_plugin_schema_version"] == (
        manifest.plugin_schema_version
    )
    assert config_data["manifest_sage_version"] == manifest.sage_version
    assert config_data["manifest_sage_git_revision"] == manifest.sage_git_revision
    assert config_data["manifest_mypy_min_version"] == manifest.mypy_min_version
    assert config_data["manifest_mypy_max_version"] == manifest.mypy_max_version
    assert config_data["manifest_source_module_digest"] == (
        refreshed_manifest.source_module_digest
    )
    assert manifest.source_module_by_module == {FIXTURE_MODULE: DIAMOND_SOURCE_MODULE}


def test_stale_reason_detects_missing_file(tmp_path: Path) -> None:
    """_source_modules_stale_reason returns the 'file is missing' diagnostic.

    The plugin debug-manifest path regenerates stubs before validation, so the
    file-missing branch cannot be exercised via the full plugin init.  The
    detection function itself is the owned unit; test it directly.
    """
    missing_path = tmp_path / "gone.py"
    # Never created — simulates a deleted source file.
    record = SourceModuleRecord(
        module="some.source.module",
        path=str(missing_path),
        sha256="a" * 64,
        mtime_ns=1_000_000_000,
    )
    reason = _source_modules_stale_reason((record,))
    assert reason == (
        "Stale Sage category source module metadata for "
        "some.source.module: file is missing"
    ), reason


def test_stale_reason_detects_mtime_mismatch(tmp_path: Path) -> None:
    """_source_modules_stale_reason returns the mtime_ns-mismatch diagnostic.

    The sha256-mismatch branch is exercised through the full plugin integration
    test (test_plugin_fails_clearly_for_stale_source_module_metadata).  The
    mtime_ns branch is only reachable when the file exists but has been touched;
    testing it directly against the detection function keeps the integration test
    fast and the unit test precise.
    """
    source_path = tmp_path / "source.py"
    source_path.write_text("x = 1\n")
    real_mtime_ns = source_path.stat().st_mtime_ns
    stale_mtime_ns = real_mtime_ns - 1  # one nanosecond behind
    record = SourceModuleRecord(
        module="some.source.module",
        path=str(source_path),
        sha256="a" * 64,
        mtime_ns=stale_mtime_ns,
    )
    reason = _source_modules_stale_reason((record,))
    assert reason is not None
    assert "mtime_ns mismatch" in reason, reason
    assert "some.source.module" in reason, reason


def test_plugin_fails_clearly_for_stale_source_module_metadata(
    tmp_path: Path,
) -> None:
    projections = _provider_projections(
        CATEGORY_FULLNAMES,
        roles=("parent",),
    )
    stale_source_module = DIAMOND_SOURCE_MODULE.model_copy(
        update={"sha256": "0" * 64}
    )
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            tuple(projections.values()),
            source_modules=(stale_source_module,),
        ),
        source_modules=(stale_source_module,),
    )
    manifest_path = tmp_path / "stale-source-module.json"
    config_path = tmp_path / "mypy.ini"
    write_manifest(manifest_path, manifest)
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)

    with pytest.raises(CompileError) as raised:
        SageCategoryProjectionPlugin(options)

    assert raised.value.messages == [
        "Stale Sage category source module metadata for "
        f"{FIXTURE_MODULE}: sha256 mismatch"
    ]


def test_plugin_fails_clearly_when_manifest_option_is_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)

    with pytest.raises(CompileError) as raised:
        SageCategoryProjectionPlugin(options)

    assert f"[{CONFIG_SECTION}] section in {config_path} must specify either " in raised.value.messages[0]
    assert "'manifest' (debug/pregenerated path) or 'packages' (auto-generation)" in raised.value.messages[0]


def test_plugin_fails_clearly_when_manifest_file_is_missing(tmp_path: Path) -> None:
    manifest_path = tmp_path / "missing-manifest.json"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)

    with pytest.raises(CompileError) as raised:
        SageCategoryProjectionPlugin(options)

    assert raised.value.messages == [
        f"Could not read Sage category projection manifest {manifest_path}: "
        "file is missing"
    ]


def test_plugin_fails_clearly_for_invalid_manifest_schema(tmp_path: Path) -> None:
    projections = _provider_projections(
        CATEGORY_FULLNAMES,
        roles=("parent",),
    )
    valid_manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            tuple(projections.values()),
        ),
    )
    payload = valid_manifest.model_dump(mode="json")
    payload["plugin_schema_version"] = "999"
    manifest_path = tmp_path / "invalid-plugin-schema.json"
    config_path = tmp_path / "mypy.ini"
    manifest_path.write_text(json.dumps(payload))
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)

    with pytest.raises(CompileError) as raised:
        SageCategoryProjectionPlugin(options)

    assert raised.value.messages == [
        "Invalid Sage category projection manifest "
        f"{manifest_path}: plugin_schema_version: Input should be '1'"
    ]


def test_normalize_role_name_maps_all_documented_variants_to_canonical_literals() -> None:
    """_normalize_role_name must accept every documented user-facing variant.

    The plugin config accepts multiple spellings of homset roles because users
    copying from examples may use spaces or CamelCase.  A missing or misspelled
    entry in the role_map would silently pass through and then fail in _parse_roles
    with an opaque "Invalid role" error instead of the correct canonical form.
    """
    # Canonical forms map to themselves
    assert _normalize_role_name("parent") == "parent"
    assert _normalize_role_name("element") == "element"
    assert _normalize_role_name("subcategory") == "subcategory"
    assert _normalize_role_name("morphism") == "morphism"
    assert _normalize_role_name("homset_parent") == "homset_parent"
    assert _normalize_role_name("homset_element") == "homset_element"

    # Space-separated variants: common in hand-written INI files
    assert _normalize_role_name("homset parent") == "homset_parent"
    assert _normalize_role_name("homset element") == "homset_element"

    # No-separator camelCase-like variants
    assert _normalize_role_name("homsetparent") == "homset_parent"
    assert _normalize_role_name("homsetelement") == "homset_element"

    # Case insensitive (lowercasing happens before map lookup)
    assert _normalize_role_name("Parent") == "parent"
    assert _normalize_role_name("PARENT") == "parent"
    assert _normalize_role_name("HomsetParent") == "homset_parent"
    assert _normalize_role_name("Homset Parent") == "homset_parent"

    # Unknown names pass through unchanged so _parse_roles can produce a clear error
    assert _normalize_role_name("badrolename") == "badrolename"
    assert _normalize_role_name("") == ""


def test_plugin_fails_clearly_for_invalid_role_config(tmp_path: Path) -> None:
    """Plugin must reject unrecognised role strings in the config with a clear error.

    The role list in mypy.ini is user-controlled; a typo or unsupported role
    string must produce an actionable CompileError rather than silently falling
    back to no projection or mapping to the wrong role.
    """
    cache_dir = tmp_path / "cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                f"[{CONFIG_SECTION}]",
                "packages = tests.fixtures.invariant_core.diamond_runtime",
                "roles = badrolename",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)

    with pytest.raises(CompileError) as raised:
        SageCategoryProjectionPlugin(options)

    assert any("badrolename" in msg for msg in raised.value.messages), (
        "Expected CompileError to name the invalid role 'badrolename'; "
        f"got messages: {raised.value.messages}"
    )


def test_plugin_config_parser_strips_inline_comments(tmp_path: Path) -> None:
    """_parse_multiline_option must strip inline # comments from config values.

    Inline comments are documented as valid in the [sage-mypy-category-plugin]
    section.  If stripping were broken, the package or role string would include
    the comment text and discovery / role parsing would fail.
    """
    cache_dir = tmp_path / "cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                f"[{CONFIG_SECTION}]",
                "packages =",
                # Inline comment after the package name — must be stripped.
                "    tests.fixtures.invariant_core.diamond_runtime  # diamond fixture",
                "roles =",
                "    parent  # the parent provider role",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)

    # The plugin must start without error: comments are stripped, package and
    # role names are clean.  If the package string retained " # diamond fixture",
    # discover_category_fullnames would fail or return empty and raise CompileError.
    plugin = SageCategoryProjectionPlugin(options)
    assert FIXTURE_MODULE in plugin._source_modules, (
        "diamond_runtime fixture must appear as a source module — "
        "comment stripping likely failed if the plugin raised CompileError above"
    )
    # parent role only — element/homset providers must not appear in projections.
    assert all(
        ".ParentMethods" in provider or ".parent_class" in provider
        for provider in plugin._projection_by_provider
    ), "Only parent-role providers expected when roles = parent"


def test_plugin_passthrough_when_no_config_section(tmp_path: Path) -> None:
    """Plugin listed in [mypy] plugins but no [sage-mypy-category-plugin] section.

    Proves that an unconfigured plugin is a safe no-op: no CompileError, no
    projections, no stubs.  Needed so global mypy configs can list the plugin
    without requiring every project to configure it.
    """
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)

    plugin = SageCategoryProjectionPlugin(options)

    # Passthrough: no projections, no manifest path, no stubs
    assert plugin._projection_by_provider == {}
    assert plugin._manifest_path is None
    assert plugin._manifest.projections == ()
    assert plugin.get_customize_class_mro_hook("any.fullname") is None
    assert plugin.report_config_data(None) == {"passthrough": "true"}  # type: ignore[arg-type]


def test_plugin_fails_clearly_when_no_categories_found_in_packages(
    tmp_path: Path,
) -> None:
    """Plugin must report a clear error when the configured packages yield no categories.

    Covers the 'no category classes found' branch in _generate_and_cache.
    tests.fixtures.invariant_core.local_wrapper defines LocalCategoryBase whose
    super_categories is still abstract (not overridden), so discover_category_fullnames
    returns an empty tuple and the plugin cannot proceed.
    """
    cache_dir = tmp_path / "cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                f"[{CONFIG_SECTION}]",
                "packages = tests.fixtures.invariant_core.local_wrapper",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)

    with pytest.raises(CompileError) as raised:
        SageCategoryProjectionPlugin(options)

    assert any(
        "No Sage category classes found" in msg for msg in raised.value.messages
    ), raised.value.messages


def test_plugin_generates_manifest_from_packages_config(tmp_path: Path) -> None:
    """Package config auto-generates the production projection manifest."""
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.diamond_runtime",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)
    options.ignore_missing_imports = True

    plugin = SageCategoryProjectionPlugin(options)

    # Manifest was generated
    manifest_path = cache_dir / "projection-manifest.json"
    assert manifest_path.is_file(), "Plugin should have generated manifest"
    manifest = json.loads(manifest_path.read_text())
    assert len(manifest["projections"]) == 4, "Diamond fixture has 4 categories"

    assert not (cache_dir / "stubs").exists(), (
        "Production package mode must not generate upstream Sage stubs"
    )

    # Projections are loaded correctly
    bottom_provider = (
        "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods"
    )
    assert bottom_provider in plugin._projection_by_provider


def test_plugin_regenerates_from_clean_cache(tmp_path: Path) -> None:
    """Phase 1A: plugin init regenerates when no cache exists."""
    cache_dir = tmp_path / "sage-category-cache"
    # Ensure clean state
    assert not cache_dir.exists()

    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.diamond_runtime",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)
    options.ignore_missing_imports = True

    _plugin = SageCategoryProjectionPlugin(options)

    # Cache was created
    assert cache_dir.is_dir()
    assert (cache_dir / "projection-manifest.json").is_file()
    assert not (cache_dir / "stubs").exists()

    # Second init from same cache works (idempotency)
    _plugin2 = SageCategoryProjectionPlugin(options)
    assert (cache_dir / "projection-manifest.json").is_file()


def test_plugin_reuses_cache_on_second_init_without_regenerating(tmp_path: Path) -> None:
    """Phase 7 E2: when the cached manifest is fresh, the plugin reuses it verbatim.

    The manifest file must NOT be rewritten on a cache hit.  We verify this by
    capturing the mtime_ns of the manifest file immediately after the first init
    and asserting that it is unchanged after the second init.

    Additionally the ``semantic_projection_digest`` must be identical across both
    initialisations — proving the same projection graph was loaded both times.
    """
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.diamond_runtime",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)
    options.ignore_missing_imports = True

    # First init — cold cache, manifest is generated.
    plugin1 = SageCategoryProjectionPlugin(options)
    manifest_path = cache_dir / "projection-manifest.json"
    assert manifest_path.is_file()
    mtime_after_first_init = manifest_path.stat().st_mtime_ns
    digest_after_first_init = plugin1._manifest.semantic_projection_digest

    # Second init — cache is fresh; manifest must not be rewritten.
    plugin2 = SageCategoryProjectionPlugin(options)
    mtime_after_second_init = manifest_path.stat().st_mtime_ns

    assert mtime_after_second_init == mtime_after_first_init, (
        "Manifest was rewritten on cache hit — plugin regenerated unnecessarily"
    )
    assert plugin2._manifest.semantic_projection_digest == digest_after_first_init, (
        "semantic_projection_digest changed across cache-hit inits — projection graph drifted"
    )


def test_plugin_detects_stale_source_and_regenerates_in_packages_mode(
    tmp_path: Path,
) -> None:
    """Phase 7 E3: mutating a source file triggers cache invalidation and regeneration.

    When a provider source file's mtime_ns changes after the manifest was generated,
    ``_try_load_cached_manifest`` must detect the staleness and return None, causing
    the plugin to regenerate the manifest without raising a CompileError.

    The test bumps the fixture source file's mtime by 1 ns to simulate a save, then
    restores it in a try/finally to leave the repo directory unmodified.
    """
    import os

    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.diamond_runtime",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)
    options.ignore_missing_imports = True

    # First init — cold cache, manifest generated.
    SageCategoryProjectionPlugin(options)
    manifest_path = cache_dir / "projection-manifest.json"
    assert manifest_path.is_file()
    mtime_after_first_init = manifest_path.stat().st_mtime_ns

    # Identify a tracked source module (the fixture package __init__ or first .py).
    manifest = load_manifest(manifest_path)
    tracked_paths = [
        Path(record.path)
        for record in manifest.source_modules
        if Path(record.path).suffix == ".py" and Path(record.path).exists()
    ]
    assert tracked_paths, "Manifest must track at least one .py source module"
    source_to_touch = tracked_paths[0]
    original_stat = source_to_touch.stat()
    original_atime = original_stat.st_atime_ns
    original_mtime = original_stat.st_mtime_ns

    # Bump mtime_ns by 1 ns — simulates a file save without changing content.
    try:
        os.utime(
            source_to_touch,
            ns=(original_atime, original_mtime + 1),
        )

        # Second init — stale source detected → manifest regenerated.
        SageCategoryProjectionPlugin(options)
        mtime_after_second_init = manifest_path.stat().st_mtime_ns

        assert mtime_after_second_init > mtime_after_first_init, (
            "Manifest mtime did not advance after stale-source regeneration — "
            "plugin failed to detect the source mutation and regenerate"
        )
    finally:
        # Restore the original mtime so the repo is not dirtied.
        os.utime(source_to_touch, ns=(original_atime, original_mtime))


def test_plugin_recovers_from_corrupt_cache_in_packages_mode(tmp_path: Path) -> None:
    """Phase 7 E6: a corrupted cache manifest triggers regeneration, not a hard failure.

    When the cached ``projection-manifest.json`` contains invalid JSON or fails
    Pydantic validation, ``_try_load_cached_manifest`` logs to stderr and returns
    None.  The plugin then runs full generation and writes a valid replacement.
    No ``CompileError`` should be raised.
    """
    cache_dir = tmp_path / "sage-category-cache"
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.diamond_runtime",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)
    options.ignore_missing_imports = True

    # First init — generates valid cache.
    SageCategoryProjectionPlugin(options)
    manifest_path = cache_dir / "projection-manifest.json"
    assert manifest_path.is_file()

    # Corrupt the manifest with invalid JSON.
    manifest_path.write_text("{ this is not valid JSON !!!")

    # Second init — corrupt manifest detected → graceful regeneration → no CompileError.
    plugin_after_recovery = SageCategoryProjectionPlugin(options)

    # The manifest must now be a valid, loadable file again.
    recovered_manifest = load_manifest(manifest_path)
    assert recovered_manifest.projections, (
        "Recovered manifest must contain projections after regeneration from corrupt cache"
    )
    assert plugin_after_recovery._manifest.semantic_projection_digest == (
        recovered_manifest.semantic_projection_digest
    ), "Plugin's loaded manifest must match the regenerated manifest on disk"


def test_plugin_package_mode_preserves_existing_mypy_path(tmp_path: Path) -> None:
    cache_dir = tmp_path / "sage-category-cache"
    preexisting_path = tmp_path / "existing-mypy-path"
    preexisting_path.mkdir()
    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                "packages = tests.fixtures.invariant_core.diamond_runtime",
                "roles = parent",
                f"cache_dir = {cache_dir}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)
    options.ignore_missing_imports = True
    options.mypy_path = [str(preexisting_path)]

    SageCategoryProjectionPlugin(options)

    assert options.mypy_path == [str(preexisting_path)]
    assert not (cache_dir / "stubs").exists()


def test_plugin_debug_manifest_still_works(tmp_path: Path) -> None:
    """Phase 1A: backward-compatible 'manifest = ...' debug path still functions."""
    projections = _provider_projections(
        CATEGORY_FULLNAMES,
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
    manifest_path = tmp_path / "manifest.json"
    write_manifest(manifest_path, manifest)

    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)

    plugin = SageCategoryProjectionPlugin(options)

    bottom_provider = (
        "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods"
    )
    assert bottom_provider in plugin._projection_by_provider


def test_plugin_debug_manifest_refreshes_source_module_metadata_in_place(
    tmp_path: Path,
) -> None:
    projections = tuple(
        _provider_projections(CATEGORY_FULLNAMES, roles=("parent",)).values()
    )
    source_modules = _write_projected_provider_stubs(
        tmp_path / "pregenerated-stubs",
        projections=projections,
    )
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=projections,
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            projections,
            source_modules=source_modules,
        ),
        source_modules=source_modules,
    )
    manifest_path = tmp_path / "manifest.json"
    write_manifest(manifest_path, manifest)

    config_path = tmp_path / "mypy.ini"
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )
    options = Options()
    options.config_file = str(config_path)
    options.ignore_missing_imports = True

    plugin = SageCategoryProjectionPlugin(options)

    refreshed_manifest = load_manifest(manifest_path)
    assert plugin._manifest_path == manifest_path
    assert refreshed_manifest.source_modules == plugin._manifest.source_modules
    assert any(record.module == "_sage_category_types" for record in refreshed_manifest.source_modules)


def test_plugin_reports_manifest_drift_and_rebuilds_projection(
    tmp_path: Path,
) -> None:
    projections = _provider_projections(
        CATEGORY_FULLNAMES,
        roles=("parent",),
    )
    original_projection = projections[BOTTOM_PROVIDER]
    original_mro = original_projection.provider_mro
    drifted_mro = (
        original_mro[0],
        original_mro[2],
        original_mro[1],
        *original_mro[3:],
    )
    drifted_projection = original_projection.model_copy(
        update={"provider_mro": drifted_mro}
    )
    drifted_projections = tuple(
        projection
        if projection.provider != BOTTOM_PROVIDER
        else drifted_projection
        for projection in projections.values()
    )
    original_manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            tuple(projections.values()),
        ),
    )
    drifted_manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=drifted_projections,
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            drifted_projections,
        ),
    )
    manifest_path = tmp_path / "drifting-projections.json"
    config_path = tmp_path / "mypy.ini"
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

    write_manifest(manifest_path, original_manifest)
    first_config_data = _plugin_config_data(config_path)
    first_result = _build_fixture(config_path, tmp_path)
    first_info = _nested_typeinfo(
        first_result,
        module=FIXTURE_MODULE,
        outer="BottomCategory",
        inner="ParentMethods",
    )

    write_manifest(manifest_path, drifted_manifest)
    second_config_data = _plugin_config_data(config_path)
    second_result = _build_fixture(config_path, tmp_path)
    second_info = _nested_typeinfo(
        second_result,
        module=FIXTURE_MODULE,
        outer="BottomCategory",
        inner="ParentMethods",
    )

    assert original_manifest.semantic_projection_digest != (
        drifted_manifest.semantic_projection_digest
    )
    assert first_config_data["manifest_digest"] != second_config_data["manifest_digest"]
    assert first_config_data["manifest_semantic_projection_digest"] != (
        second_config_data["manifest_semantic_projection_digest"]
    )
    assert first_result.errors == []
    assert second_result.errors == []
    assert tuple(info.fullname for info in first_info.mro) == (
        *original_mro,
        "builtins.object",
    )
    assert tuple(info.fullname for info in second_info.mro) == (
        *drifted_mro,
        "builtins.object",
    )


def _build_fixture(
    config_path: Path,
    tmp_path: Path,
    *,
    fixture_path: Path = FIXTURE_PATH,
    fixture_module: str = FIXTURE_MODULE,
    fixture_sources: Sequence[tuple[Path, str]] | None = None,
    mypy_path_entries: Sequence[Path] = (REPO_ROOT,),
) -> BuildResult:
    sources = fixture_sources or ((fixture_path, fixture_module),)
    options = Options()
    options.config_file = str(config_path)
    options.plugins = ["sage_mypy_category_plugin.plugin"]
    options.incremental = False
    options.cache_dir = str(tmp_path / "mypy-cache")
    options.mypy_path = [str(path) for path in mypy_path_entries]
    options.ignore_missing_imports = True
    return build(
        sources=[
            BuildSource(str(source_path), source_module, None)
            for source_path, source_module in sources
        ],
        options=options,
    )


def _plugin_config_data(config_path: Path) -> dict[str, str]:
    options = Options()
    options.config_file = str(config_path)
    return SageCategoryProjectionPlugin(options).report_config_data(
        ctx=None,  # type: ignore[arg-type]
    )


def _build_fixture_without_plugin(
    tmp_path: Path,
    *,
    fixture_path: Path = FIXTURE_PATH,
    fixture_module: str = FIXTURE_MODULE,
    fixture_sources: Sequence[tuple[Path, str]] | None = None,
    mypy_path_entries: Sequence[Path] = (REPO_ROOT,),
) -> BuildResult:
    sources = fixture_sources or ((fixture_path, fixture_module),)
    options = Options()
    options.incremental = False
    options.cache_dir = str(tmp_path / "baseline-mypy-cache")
    options.mypy_path = [str(path) for path in mypy_path_entries]
    options.ignore_missing_imports = True
    return build(
        sources=[
            BuildSource(str(source_path), source_module, None)
            for source_path, source_module in sources
        ],
        options=options,
    )


def _nested_typeinfo(
    result: BuildResult,
    *,
    module: str,
    outer: str,
    inner: str,
) -> TypeInfo:
    outer_node = result.files[module].names[outer].node
    assert isinstance(outer_node, TypeInfo)

    inner_node = outer_node.names[inner].node
    assert isinstance(inner_node, TypeInfo)
    return inner_node


def _inner_typeinfo(outer_info: TypeInfo, inner: str) -> TypeInfo:
    inner_node = outer_info.names[inner].node
    assert isinstance(inner_node, TypeInfo)
    return inner_node


def _contains_error_fragment(result: BuildResult, fragment: str) -> bool:
    return any(fragment in error for error in result.errors)


def _write_visible_sage_provider_stubs(stub_root: Path) -> None:
    categories = stub_root / "sage" / "categories"
    categories.mkdir(parents=True)
    (stub_root / "sage" / "__init__.pyi").write_text("")
    (categories / "__init__.pyi").write_text("")
    (categories / "homsets.pyi").write_text(
        "\n".join(
            (
                "class HomsetsCategory: ...",
                "class Homsets:",
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
                "    class ElementMethods: ...",
                "",
            )
        )
    )
    (categories / "finite_sets.pyi").write_text(
        "\n".join(
            (
                "class FiniteSets:",
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


def _write_projected_provider_stubs(
    stub_root: Path,
    *,
    projections: tuple[ProviderProjection, ...],
) -> tuple[SourceModuleRecord, ...]:
    manifest_source_modules = _source_module_records_for_modules(
        stub_root,
        _projected_source_module_names(projections),
    )
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=projections,
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            projections,
        ),
        source_modules=manifest_source_modules,
    )
    written_source_modules = {
        record.module: record for record in write_generated_stub_tree(stub_root, manifest)
    }
    for source_module in manifest_source_modules:
        if source_module.module not in written_source_modules:
            placeholder = _write_empty_stub_module(stub_root, source_module.module)
            written_source_modules[placeholder.module] = placeholder
    return tuple(
        record
        for module, record in sorted(
            written_source_modules.items(),
            key=lambda item: item[0],
        )
    )


def _source_module_records_for_modules(
    stub_root: Path,
    module_names: tuple[str, ...],
) -> tuple[SourceModuleRecord, ...]:
    return tuple(
        SourceModuleRecord(
            module=module_name,
            path=str(stub_root.joinpath(*module_name.split(".")).with_suffix(".pyi")),
            sha256="0" * 64,
            mtime_ns=0,
        )
        for module_name in module_names
    )


def _write_empty_stub_module(stub_root: Path, module_name: str) -> SourceModuleRecord:
    path = stub_root.joinpath(*module_name.split(".")).with_suffix(".pyi")
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_stub_package_markers(stub_root, path.parent)
    path.write_text("")
    path_bytes = path.read_bytes()
    path_stat = path.stat()
    return SourceModuleRecord(
        module=module_name,
        path=str(path),
        sha256=sha256(path_bytes).hexdigest(),
        mtime_ns=path_stat.st_mtime_ns,
    )


def _write_stub_package_markers(stub_root: Path, package_dir: Path) -> None:
    current = package_dir
    packages: list[Path] = []
    while current != stub_root:
        packages.append(current)
        current = current.parent
    for package in reversed(packages):
        (package / "__init__.pyi").write_text("")


def _projected_source_module_names(
    projections: tuple[ProviderProjection, ...],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            _importable_module_name(fullname)
            for fullname in _projection_fullnames(projections)
            if not _is_intrinsic_fullname(fullname)
        )
    )


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


def _is_intrinsic_fullname(fullname: str) -> bool:
    return fullname == "builtins" or fullname.startswith("builtins.")


def _importable_module_name(fullname: str) -> str:
    parts = fullname.split(".")
    for split_index in range(len(parts), 0, -1):
        module_name = ".".join(parts[:split_index])
        try:
            import_module(module_name)
        except ModuleNotFoundError:
            continue
        return module_name
    raise AssertionError(f"Could not find importable module for {fullname!r}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 mutation proof helpers and tests (5A–5G)
#
# Each test proves: provider_mro mutations (truncation and reordering) propagate
# exactly to TypeInfo.mro.  This is the structural invariant: the plugin writes
# what the manifest says, no more and no less.  A corrupted manifest therefore
# produces a detectable, quantifiably wrong TypeInfo graph.
# ─────────────────────────────────────────────────────────────────────────────


def _with_corrupted_provider_mro(
    projections: dict[str, ProviderProjection],
    target: str,
    corrupted_mro: tuple[str, ...],
) -> dict[str, ProviderProjection]:
    """Return projections dict with target's provider_mro replaced.

    Retains only provider_bases entries still present in corrupted_mro[1:],
    preserving the schema invariant provider_bases ⊆ provider_mro[1:].
    """
    original = projections[target]
    return {
        **projections,
        target: original.model_copy(
            update={
                "provider_mro": corrupted_mro,
                "provider_bases": tuple(
                    b for b in original.provider_bases if b in corrupted_mro[1:]
                ),
            }
        ),
    }


def _write_mutation_manifest_and_config(
    tmp_path: Path,
    projections: dict[str, ProviderProjection],
    source_modules: tuple["SourceModuleRecord", ...],
    label: str,
    *,
    unsupported_providers: tuple["UnsupportedProviderRecord", ...] = (),
) -> Path:
    """Write a manifest and plugin config for a mutation test; return config path."""
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
        unsupported_providers=unsupported_providers,
        external_runtime_classes=external_runtime_class_records_for_test_manifest(
            tuple(projections.values()),
            source_modules=source_modules,
        ),
        source_modules=source_modules,
    )
    manifest_path = tmp_path / f"mutation-{label}.json"
    config_path = tmp_path / f"mutation-{label}.ini"
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


def test_phase5A_nested_axiom_provider_mro_mutations_are_structurally_detectable(
    tmp_path: Path,
) -> None:
    """Phase 5A mutation proof: corrupted provider_mro propagates to TypeInfo.mro.

    Truncating the last projected base and reordering two intermediate bases
    each produce a TypeInfo.mro that differs from the oracle-correct projection
    for AxiomRootCategory.Finite.ParentMethods.
    """
    projections = _provider_projections(NESTED_AXIOM_FULLNAMES, roles=("parent",))
    oracle_mro = projections[NESTED_AXIOM_PROVIDER].provider_mro
    stub_root = tmp_path / "stubs"
    source_modules = _write_projected_provider_stubs(
        stub_root, projections=tuple(projections.values())
    )

    def _extract_mro(corrupted_mro: tuple[str, ...], label: str) -> tuple[str, ...]:
        corrupted = _with_corrupted_provider_mro(projections, NESTED_AXIOM_PROVIDER, corrupted_mro)
        config_path = _write_mutation_manifest_and_config(
            tmp_path, corrupted, source_modules, label
        )
        result = _build_fixture(
            config_path,
            tmp_path,
            fixture_path=AXIOM_FIXTURE_PATH,
            fixture_module=AXIOM_FIXTURE_MODULE,
            mypy_path_entries=(REPO_ROOT, stub_root),
        )
        axiom_cat = result.files[AXIOM_FIXTURE_MODULE].names["AxiomRootCategory"].node
        assert isinstance(axiom_cat, TypeInfo)
        axiom_finite = _inner_typeinfo(axiom_cat, "Finite")
        axiom_parent = _inner_typeinfo(axiom_finite, "ParentMethods")
        return tuple(info.fullname for info in axiom_parent.mro)

    oracle_typeinfo_mro = (*oracle_mro, "builtins.object")

    # Truncation: remove last base (sage.categories.objects.Objects.ParentMethods)
    truncated_mro = oracle_mro[:-1]
    truncated_typeinfo_mro = _extract_mro(truncated_mro, "5a-truncated")
    assert truncated_typeinfo_mro != oracle_typeinfo_mro, (
        f"Truncated provider_mro must produce a different TypeInfo.mro; "
        f"got {truncated_typeinfo_mro!r} vs oracle {oracle_typeinfo_mro!r}"
    )
    assert len(truncated_typeinfo_mro) < len(oracle_typeinfo_mro), (
        f"Truncated TypeInfo.mro must be shorter than oracle; "
        f"got {truncated_typeinfo_mro!r}"
    )

    # Reordering: swap positions [1] and [2] (FiniteSets.PM ↔ AxiomRootCategory.PM)
    reordered_mro = (oracle_mro[0], oracle_mro[2], oracle_mro[1], *oracle_mro[3:])
    reordered_typeinfo_mro = _extract_mro(reordered_mro, "5a-reordered")
    assert reordered_typeinfo_mro != oracle_typeinfo_mro, (
        f"Reordered provider_mro must produce a different TypeInfo.mro; "
        f"got {reordered_typeinfo_mro!r} vs oracle {oracle_typeinfo_mro!r}"
    )
    assert reordered_typeinfo_mro == (*reordered_mro, "builtins.object"), (
        f"Reordered TypeInfo.mro must exactly reflect the manifest MRO; "
        f"got {reordered_typeinfo_mro!r}"
    )


def test_phase5B_linked_axiom_provider_mro_mutations_are_structurally_detectable(
    tmp_path: Path,
) -> None:
    """Phase 5B mutation proof: corrupted provider_mro propagates to TypeInfo.mro.

    Truncating and reordering the linked axiom provider's MRO each produce a
    TypeInfo.mro that differs from the oracle-correct projection for
    LinkedFiniteAxiomCategory.ParentMethods.
    """
    projections = _provider_projections(LINKED_AXIOM_FULLNAMES, roles=("parent",))
    oracle_mro = projections[LINKED_AXIOM_PROVIDER].provider_mro
    stub_root = tmp_path / "stubs"
    source_modules = _write_projected_provider_stubs(
        stub_root, projections=tuple(projections.values())
    )
    fixture_sources = (
        (LINKED_AXIOM_ROOT_PATH, LINKED_AXIOM_ROOT_MODULE),
        (LINKED_AXIOM_FINITE_PATH, LINKED_AXIOM_FINITE_MODULE),
    )

    def _extract_mro(corrupted_mro: tuple[str, ...], label: str) -> tuple[str, ...]:
        corrupted = _with_corrupted_provider_mro(projections, LINKED_AXIOM_PROVIDER, corrupted_mro)
        config_path = _write_mutation_manifest_and_config(
            tmp_path, corrupted, source_modules, label
        )
        result = _build_fixture(
            config_path,
            tmp_path,
            fixture_sources=fixture_sources,
            mypy_path_entries=(REPO_ROOT, stub_root),
        )
        linked_cat = result.files[LINKED_AXIOM_FINITE_MODULE].names[
            "LinkedFiniteAxiomCategory"
        ].node
        assert isinstance(linked_cat, TypeInfo)
        linked_parent = _inner_typeinfo(linked_cat, "ParentMethods")
        return tuple(info.fullname for info in linked_parent.mro)

    oracle_typeinfo_mro = (*oracle_mro, "builtins.object")

    # Truncation: remove last base (sage.categories.objects.Objects.ParentMethods)
    truncated_mro = oracle_mro[:-1]
    truncated_typeinfo_mro = _extract_mro(truncated_mro, "5b-truncated")
    assert truncated_typeinfo_mro != oracle_typeinfo_mro, (
        f"Truncated provider_mro must produce a different TypeInfo.mro; "
        f"got {truncated_typeinfo_mro!r}"
    )
    assert len(truncated_typeinfo_mro) < len(oracle_typeinfo_mro)

    # Reordering: swap positions [1] and [2] (FiniteSets.PM ↔ LinkedAxiomRootCategory.PM)
    reordered_mro = (oracle_mro[0], oracle_mro[2], oracle_mro[1], *oracle_mro[3:])
    reordered_typeinfo_mro = _extract_mro(reordered_mro, "5b-reordered")
    assert reordered_typeinfo_mro != oracle_typeinfo_mro, (
        f"Reordered provider_mro must produce a different TypeInfo.mro; "
        f"got {reordered_typeinfo_mro!r}"
    )
    assert reordered_typeinfo_mro == (*reordered_mro, "builtins.object")


def test_phase5C_cartesian_products_provider_mro_mutations_are_structurally_detectable(
    tmp_path: Path,
) -> None:
    """Phase 5C mutation proof: corrupted CartesianProducts provider_mro propagates.

    Truncating and reordering Sets.CartesianProducts.ParentMethods.provider_mro
    each produce a TypeInfo.mro that differs from the oracle-correct projection.
    """
    projections = _provider_projections(
        (FUNCTORIAL_CARTESIAN_CATEGORY,), roles=("parent", "element")
    )
    oracle_mro = projections[FUNCTORIAL_CARTESIAN_PARENT_PROVIDER].provider_mro
    stub_root = tmp_path / "stubs"
    source_modules = _write_projected_provider_stubs(
        stub_root, projections=tuple(projections.values())
    )
    consumer_path = tmp_path / "cartesian_consumer.py"
    consumer_path.write_text(
        "\n".join(
            (
                "from sage.categories.sets_cat import Sets",
                "Sets.CartesianProducts.ParentMethods",
                "",
            )
        )
    )

    def _extract_mro(corrupted_mro: tuple[str, ...], label: str) -> tuple[str, ...]:
        corrupted = _with_corrupted_provider_mro(
            projections, FUNCTORIAL_CARTESIAN_PARENT_PROVIDER, corrupted_mro
        )
        config_path = _write_mutation_manifest_and_config(
            tmp_path, corrupted, source_modules, label
        )
        result = _build_fixture(
            config_path,
            tmp_path,
            fixture_sources=((consumer_path, "cartesian_consumer"),),
            mypy_path_entries=(stub_root,),
        )
        sets_info = result.files["sage.categories.sets_cat"].names["Sets"].node
        assert isinstance(sets_info, TypeInfo)
        cp_info = _inner_typeinfo(sets_info, "CartesianProducts")
        parent_info = _inner_typeinfo(cp_info, "ParentMethods")
        return tuple(info.fullname for info in parent_info.mro)

    oracle_typeinfo_mro = (*oracle_mro, "builtins.object")

    # Truncation: remove last base (sage.categories.objects.Objects.ParentMethods)
    truncated_mro = oracle_mro[:-1]
    truncated_typeinfo_mro = _extract_mro(truncated_mro, "5c-truncated")
    assert truncated_typeinfo_mro != oracle_typeinfo_mro, (
        f"Truncated provider_mro must produce a different TypeInfo.mro; "
        f"got {truncated_typeinfo_mro!r}"
    )
    assert len(truncated_typeinfo_mro) < len(oracle_typeinfo_mro)

    # Reordering: swap positions [1] and [2] (Sets.PM ↔ Objects.PM)
    reordered_mro = (oracle_mro[0], oracle_mro[2], oracle_mro[1], *oracle_mro[3:])
    reordered_typeinfo_mro = _extract_mro(reordered_mro, "5c-reordered")
    assert reordered_typeinfo_mro != oracle_typeinfo_mro, (
        f"Reordered provider_mro must produce a different TypeInfo.mro; "
        f"got {reordered_typeinfo_mro!r}"
    )
    assert reordered_typeinfo_mro == (*reordered_mro, "builtins.object")


def test_phase5D_tensor_products_provider_mro_mutations_are_structurally_detectable(
    tmp_path: Path,
) -> None:
    """Phase 5D mutation proof: corrupted TensorProducts provider_mro propagates.

    Truncating and reordering Modules.TensorProducts.ParentMethods.provider_mro
    each produce a TypeInfo.mro that differs from the oracle-correct projection.
    """
    projections = _provider_projections(
        (FUNCTORIAL_TENSOR_CATEGORY,), roles=("parent",)
    )
    oracle_mro = projections[FUNCTORIAL_TENSOR_PARENT_PROVIDER].provider_mro
    stub_root = tmp_path / "stubs"
    source_modules = _write_projected_provider_stubs(
        stub_root, projections=tuple(projections.values())
    )
    consumer_path = tmp_path / "tensor_consumer.py"
    consumer_path.write_text(
        "\n".join(
            (
                "from sage.categories.modules import Modules",
                "Modules.TensorProducts.ParentMethods",
                "",
            )
        )
    )

    def _extract_mro(corrupted_mro: tuple[str, ...], label: str) -> tuple[str, ...]:
        corrupted = _with_corrupted_provider_mro(
            projections, FUNCTORIAL_TENSOR_PARENT_PROVIDER, corrupted_mro
        )
        config_path = _write_mutation_manifest_and_config(
            tmp_path, corrupted, source_modules, label
        )
        result = _build_fixture(
            config_path,
            tmp_path,
            fixture_sources=((consumer_path, "tensor_consumer"),),
            mypy_path_entries=(stub_root,),
        )
        modules_info = result.files["sage.categories.modules"].names["Modules"].node
        assert isinstance(modules_info, TypeInfo)
        tp_info = _inner_typeinfo(modules_info, "TensorProducts")
        parent_info = _inner_typeinfo(tp_info, "ParentMethods")
        return tuple(info.fullname for info in parent_info.mro)

    oracle_typeinfo_mro = (*oracle_mro, "builtins.object")

    # Truncation: remove last base
    truncated_mro = oracle_mro[:-1]
    truncated_typeinfo_mro = _extract_mro(truncated_mro, "5d-truncated")
    assert truncated_typeinfo_mro != oracle_typeinfo_mro, (
        f"Truncated provider_mro must produce a different TypeInfo.mro; "
        f"got {truncated_typeinfo_mro!r}"
    )
    assert len(truncated_typeinfo_mro) < len(oracle_typeinfo_mro)

    # Reordering: swap positions [1] and [2] (Modules.PM ↔ Bimodules.PM)
    reordered_mro = (oracle_mro[0], oracle_mro[2], oracle_mro[1], *oracle_mro[3:])
    reordered_typeinfo_mro = _extract_mro(reordered_mro, "5d-reordered")
    assert reordered_typeinfo_mro != oracle_typeinfo_mro, (
        f"Reordered provider_mro must produce a different TypeInfo.mro; "
        f"got {reordered_typeinfo_mro!r}"
    )
    assert reordered_typeinfo_mro == (*reordered_mro, "builtins.object")


def test_phase5E_parameterized_provider_mro_mutations_are_structurally_detectable(
    tmp_path: Path,
) -> None:
    """Phase 5E mutation proof: corrupted Modules.ParentMethods provider_mro propagates.

    Truncating and reordering the parameterized Modules.ParentMethods.provider_mro
    each produce a TypeInfo.mro that differs from the oracle-correct projection.
    """
    projections = _provider_projections(PARAMETERIZED_CATEGORY_FULLNAMES, roles=("parent",))
    oracle_mro = projections[PARAMETERIZED_MODULES_PROVIDER].provider_mro
    stub_root = tmp_path / "stubs"
    source_modules = _write_projected_provider_stubs(
        stub_root, projections=tuple(projections.values())
    )
    consumer_path = tmp_path / "param_consumer.py"
    consumer_path.write_text(
        "\n".join(
            (
                "from sage.categories.modules import Modules",
                "Modules.ParentMethods",
                "",
            )
        )
    )

    def _extract_mro(corrupted_mro: tuple[str, ...], label: str) -> tuple[str, ...]:
        corrupted = _with_corrupted_provider_mro(
            projections, PARAMETERIZED_MODULES_PROVIDER, corrupted_mro
        )
        config_path = _write_mutation_manifest_and_config(
            tmp_path, corrupted, source_modules, label
        )
        result = _build_fixture(
            config_path,
            tmp_path,
            fixture_sources=((consumer_path, "param_consumer"),),
            mypy_path_entries=(stub_root,),
        )
        modules_info = result.files["sage.categories.modules"].names["Modules"].node
        assert isinstance(modules_info, TypeInfo)
        parent_info = _inner_typeinfo(modules_info, "ParentMethods")
        return tuple(info.fullname for info in parent_info.mro)

    oracle_typeinfo_mro = (*oracle_mro, "builtins.object")

    # Truncation: remove last base
    truncated_mro = oracle_mro[:-1]
    truncated_typeinfo_mro = _extract_mro(truncated_mro, "5e-truncated")
    assert truncated_typeinfo_mro != oracle_typeinfo_mro, (
        f"Truncated provider_mro must produce a different TypeInfo.mro; "
        f"got {truncated_typeinfo_mro!r}"
    )
    assert len(truncated_typeinfo_mro) < len(oracle_typeinfo_mro)

    # Reordering: swap positions [1] and [2] (Bimodules.PM ↔ RightModules.PM)
    reordered_mro = (oracle_mro[0], oracle_mro[2], oracle_mro[1], *oracle_mro[3:])
    reordered_typeinfo_mro = _extract_mro(reordered_mro, "5e-reordered")
    assert reordered_typeinfo_mro != oracle_typeinfo_mro, (
        f"Reordered provider_mro must produce a different TypeInfo.mro; "
        f"got {reordered_typeinfo_mro!r}"
    )
    assert reordered_typeinfo_mro == (*reordered_mro, "builtins.object")


def test_phase5F_homset_provider_mro_mutations_are_structurally_detectable(
    tmp_path: Path,
) -> None:
    """Phase 5F mutation proof: corrupted homset provider_mro propagates to TypeInfo.mro.

    Truncating and reordering BottomCategory.Homsets.ParentMethods.provider_mro
    each produce a TypeInfo.mro that differs from the oracle-correct projection.
    """
    homset_bottom_parent_provider = (
        f"{HOMSET_ROLES_MODULE}.BottomCategory.Homsets.ParentMethods"
    )
    projections, unsupported_providers = _provider_projections_with_unsupported(
        HOMSET_ROLES_FULLNAMES,
        roles=("homset_parent", "homset_element"),
    )
    oracle_mro = projections[homset_bottom_parent_provider].provider_mro
    stub_root = tmp_path / "stubs"
    _write_visible_sage_provider_stubs(stub_root)

    def _extract_mro(corrupted_mro: tuple[str, ...], label: str) -> tuple[str, ...]:
        corrupted = _with_corrupted_provider_mro(
            projections, homset_bottom_parent_provider, corrupted_mro
        )
        config_path = _write_mutation_manifest_and_config(
            tmp_path,
            corrupted,
            source_modules=(),
            label=label,
            unsupported_providers=unsupported_providers,
        )
        result = _build_fixture(
            config_path,
            tmp_path,
            fixture_path=HOMSET_ROLES_PATH,
            fixture_module=HOMSET_ROLES_MODULE,
            mypy_path_entries=(REPO_ROOT, stub_root),
        )
        homsets_info = _nested_typeinfo(
            result,
            module=HOMSET_ROLES_MODULE,
            outer="BottomCategory",
            inner="Homsets",
        )
        parent_info = _inner_typeinfo(homsets_info, "ParentMethods")
        return tuple(info.fullname for info in parent_info.mro)

    oracle_typeinfo_mro = (*oracle_mro, "builtins.object")

    # Truncation: remove last base (sage.categories.objects.Objects.ParentMethods)
    truncated_mro = oracle_mro[:-1]
    truncated_typeinfo_mro = _extract_mro(truncated_mro, "5f-truncated")
    assert truncated_typeinfo_mro != oracle_typeinfo_mro, (
        f"Truncated provider_mro must produce a different TypeInfo.mro; "
        f"got {truncated_typeinfo_mro!r}"
    )
    assert len(truncated_typeinfo_mro) < len(oracle_typeinfo_mro)

    # Reordering: swap positions [1] and [2]
    # (TopCategory.Homsets.PM ↔ sage.categories.homsets.Homsets.PM)
    reordered_mro = (oracle_mro[0], oracle_mro[2], oracle_mro[1], *oracle_mro[3:])
    reordered_typeinfo_mro = _extract_mro(reordered_mro, "5f-reordered")
    assert reordered_typeinfo_mro != oracle_typeinfo_mro, (
        f"Reordered provider_mro must produce a different TypeInfo.mro; "
        f"got {reordered_typeinfo_mro!r}"
    )
    assert reordered_typeinfo_mro == (*reordered_mro, "builtins.object")


def test_phase5G_morphism_provider_mro_mutations_are_structurally_detectable(
    tmp_path: Path,
) -> None:
    """Phase 5G mutation proof: corrupted morphism provider_mro propagates to TypeInfo.mro.

    Truncating and reordering BottomCategory.MorphismMethods.provider_mro each produce
    a TypeInfo.mro that differs from the oracle-correct projection.  All providers are
    source-based fixture classes; no Sage external stubs are required.
    """
    bottom_morphism_provider = f"{PROVIDER_ROLES_MODULE}.BottomCategory.MorphismMethods"
    projections = _provider_projections(PROVIDER_ROLES_FULLNAMES, roles=("morphism",))
    oracle_mro = projections[bottom_morphism_provider].provider_mro

    def _extract_mro(corrupted_mro: tuple[str, ...], label: str) -> tuple[str, ...]:
        corrupted = _with_corrupted_provider_mro(
            projections, bottom_morphism_provider, corrupted_mro
        )
        config_path = _write_mutation_manifest_and_config(
            tmp_path, corrupted, source_modules=(), label=label
        )
        result = _build_fixture(
            config_path,
            tmp_path,
            fixture_path=PROVIDER_ROLES_PATH,
            fixture_module=PROVIDER_ROLES_MODULE,
            mypy_path_entries=(REPO_ROOT,),
        )
        bottom_info = _nested_typeinfo(
            result,
            module=PROVIDER_ROLES_MODULE,
            outer="BottomCategory",
            inner="MorphismMethods",
        )
        return tuple(info.fullname for info in bottom_info.mro)

    oracle_typeinfo_mro = (*oracle_mro, "builtins.object")

    # Truncation: remove last base (TopCategory.MorphismMethods)
    truncated_mro = oracle_mro[:-1]
    truncated_typeinfo_mro = _extract_mro(truncated_mro, "5g-truncated")
    assert truncated_typeinfo_mro != oracle_typeinfo_mro, (
        f"Truncated provider_mro must produce a different TypeInfo.mro; "
        f"got {truncated_typeinfo_mro!r}"
    )
    assert len(truncated_typeinfo_mro) < len(oracle_typeinfo_mro)

    # Reordering: swap positions [1] and [2] (RightCategory.MM ↔ LeftCategory.MM)
    reordered_mro = (oracle_mro[0], oracle_mro[2], oracle_mro[1], *oracle_mro[3:])
    reordered_typeinfo_mro = _extract_mro(reordered_mro, "5g-reordered")
    assert reordered_typeinfo_mro != oracle_typeinfo_mro, (
        f"Reordered provider_mro must produce a different TypeInfo.mro; "
        f"got {reordered_typeinfo_mro!r}"
    )
    assert reordered_typeinfo_mro == (*reordered_mro, "builtins.object")
