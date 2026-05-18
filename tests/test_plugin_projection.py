from __future__ import annotations

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
    write_manifest,
)
from sage_mypy_category_plugin.oracle import provider_projections_for_categories
from sage_mypy_category_plugin.plugin import (
    CONFIG_SECTION,
    SageCategoryProjectionPlugin,
)
from sage_mypy_category_plugin.projection import ProviderProjection
from sage_mypy_category_plugin.stubs import write_generated_stub_tree

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
    roles: tuple[str, ...],
) -> dict[str, ProviderProjection]:
    return dict(_provider_projection_items(category_fullnames, roles))


@cache
def _provider_projection_items(
    category_fullnames: tuple[str, ...],
    roles: tuple[str, ...],
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
    provider_role_projections = _provider_projections(
        PROVIDER_ROLES_FULLNAMES,
        roles=("element", "subcategory", "morphism"),
    )
    homset_projections = _provider_projections(
        HOMSET_ROLES_FULLNAMES,
        roles=("homset_parent", "homset_element"),
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
        **provider_role_projections,
        **homset_projections,
        **cross_module_projections,
    }
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
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
    assert tuple(info.fullname for info in bottom_parent_info.mro) == (
        *diamond_projections[BOTTOM_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(info.fullname for info in repeated_bottom_parent_info.mro) == (
        *diamond_projections[BOTTOM_PROVIDER].provider_mro,
        "builtins.object",
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
    assert tuple(info.fullname for info in commutative_parent_info.mro) == (
        *expected_commutative_mro,
        "builtins.object",
    )
    assert expected_commutative_mro == (
        CATEGORY_SPECS_LIKE_COMMUTATIVE_PROVIDER,
        CATEGORY_SPECS_LIKE_ROOT_PROVIDER,
    )
    assert root_parent_info.fullname == CATEGORY_SPECS_LIKE_ROOT_PROVIDER

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
        assert tuple(info.fullname for info in role_info.mro) == (
            *projections[provider].provider_mro,
            "builtins.object",
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
    assert tuple(info.fullname for info in element_info.mro) == (
        *homset_projections[element_provider].provider_mro,
        "builtins.object",
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
    assert tuple(info.fullname for info in consumer_info.mro) == (
        consumer_provider,
        base_provider,
        "builtins.object",
    )


def test_plugin_reports_homset_external_provider_boundary(
    tmp_path: Path,
) -> None:
    projections = _provider_projections(
        HOMSET_ROLES_FULLNAMES,
        roles=("homset_parent", "homset_element"),
    )
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
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

    assert _contains_error_fragment(
        result,
        "sage.categories.homsets.Homsets.ParentMethods",
    )
    assert _contains_error_fragment(
        result,
        "sage.categories.sets_cat.Sets.ParentMethods",
    )
    assert _contains_error_fragment(
        result,
        "sage.categories.sets_cat.Sets.ElementMethods",
    )


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
    parameterized_projections = _provider_projections(
        PARAMETERIZED_CATEGORY_FULLNAMES,
        roles=("parent",),
    )
    projections = {
        **axiom_projections,
        **cartesian_projections,
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
    vector_spaces_parent_info = _inner_typeinfo(
        vector_spaces_info,
        "ParentMethods",
    )

    assert result.errors == []
    assert tuple(info.fullname for info in commutative_info.mro) == (
        *axiom_projections[COMMUTATIVE_RINGS_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(info.fullname for info in parent_info.mro) == (
        *cartesian_projections[FUNCTORIAL_CARTESIAN_PARENT_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(info.fullname for info in element_info.mro) == (
        *cartesian_projections[FUNCTORIAL_CARTESIAN_ELEMENT_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(info.fullname for info in modules_parent_info.mro) == (
        *parameterized_projections[PARAMETERIZED_MODULES_PROVIDER].provider_mro,
        "builtins.object",
    )
    assert tuple(info.fullname for info in vector_spaces_parent_info.mro) == (
        *parameterized_projections[PARAMETERIZED_VECTOR_SPACES_PROVIDER].provider_mro,
        "builtins.object",
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
                runtime_bases=(),
                runtime_mro=(),
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
    config_data = SageCategoryProjectionPlugin(options).report_config_data(
        ctx=None,  # type: ignore[arg-type]
    )

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
        manifest.source_module_digest
    )
    assert manifest.source_module_by_module == {FIXTURE_MODULE: DIAMOND_SOURCE_MODULE}


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

    assert raised.value.messages == [
        f"Missing manifest option in [{CONFIG_SECTION}] section of {config_path}"
    ]


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
    original_manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(projections.values()),
    )
    drifted_manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=tuple(
            projection
            if projection.provider != BOTTOM_PROVIDER
            else drifted_projection
            for projection in projections.values()
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
    source_modules = tuple(
        SourceModuleRecord(
            module=module_name,
            path=str(stub_root.joinpath(*module_name.split(".")).with_suffix(".pyi")),
            sha256="0" * 64,
            mtime_ns=0,
        )
        for module_name in _projected_provider_module_names(projections)
    )
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=projections,
        source_modules=source_modules,
    )
    return write_generated_stub_tree(stub_root, manifest)


def _projected_provider_module_names(
    projections: tuple[ProviderProjection, ...],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            _importable_module_name(provider)
            for projection in projections
            for provider in projection.provider_mro
        )
    )


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
