from __future__ import annotations

from pathlib import Path

from sage_mypy_category_plugin.manifest import load_manifest
from sage_mypy_category_plugin.oracle import provider_projections_for_categories
from sage_mypy_category_plugin import resolver

FIXTURE_MODULE = "tests.fixtures.invariant_core.diamond_runtime"
FIXTURE_CATEGORIES = (
    f"{FIXTURE_MODULE}.TopCategory",
    f"{FIXTURE_MODULE}.LeftCategory",
    f"{FIXTURE_MODULE}.RightCategory",
    f"{FIXTURE_MODULE}.BottomCategory",
)
BOTTOM_PARENT_PROVIDER = (
    f"{FIXTURE_MODULE}.BottomCategory.ParentMethods"
)
HOMSET_FIXTURE_MODULE = "tests.fixtures.invariant_core.provider_roles.homsets"
HOMSET_BOTTOM_CATEGORY = f"{HOMSET_FIXTURE_MODULE}.BottomCategory"
BOTTOM_HOMSET_PARENT_PROVIDER = (
    f"{HOMSET_FIXTURE_MODULE}.BottomCategory.Homsets.ParentMethods"
)
SHARED_HOMSET_CATEGORY = f"{HOMSET_FIXTURE_MODULE}.SharedHomsetProviderCategory"
SHARED_HOMSET_PROVIDER = f"{HOMSET_FIXTURE_MODULE}.SharedHomsetParentMethods"
COMMUTATIVE_RINGS_CATEGORY = "sage.categories.commutative_rings.CommutativeRings"
SEMIGROUPS_CATEGORY = "sage.categories.semigroups.Semigroups"
OBJECTS_PARENT_PROVIDER = "sage.categories.objects.Objects.ParentMethods"
LEFT_ZERO_SEMIGROUP = "sage.categories.examples.semigroups.LeftZeroSemigroup"
SELF_RETURN_MODULE = "tests.fixtures.invariant_core.provider_methods"
SELF_RETURN_CATEGORY = f"{SELF_RETURN_MODULE}.SelfReturnCategory"
SELF_RETURN_PROVIDER = f"{SELF_RETURN_CATEGORY}.ParentMethods"
AXIOM_FIXTURE_MODULE = "tests.fixtures.invariant_core.axioms"
NESTED_AXIOM_CATEGORY = f"{AXIOM_FIXTURE_MODULE}.AxiomRootCategory.Finite"
NESTED_AXIOM_PROVIDER = f"{NESTED_AXIOM_CATEGORY}.ParentMethods"
AXIOM_ROOT_PROVIDER = f"{AXIOM_FIXTURE_MODULE}.AxiomRootCategory.ParentMethods"
CATEGORY_SPECS_LIKE_PACKAGE = (
    "tests.fixtures.invariant_core.category_specs_like.rings"
)
CATEGORY_SPECS_LIKE_ROOT_PROVIDER = (
    f"{CATEGORY_SPECS_LIKE_PACKAGE}._RingObjectMethods"
)
CATEGORY_SPECS_LIKE_COMMUTATIVE_PROVIDER = (
    f"{CATEGORY_SPECS_LIKE_PACKAGE}.subcategories."
    "commutative._CommutativeRings.ParentMethods"
)
CATEGORY_SPECS_LIKE_NAMESPACE_PROVIDER = (
    f"{CATEGORY_SPECS_LIKE_PACKAGE}.namespace_subcategories."
    "commutative._NamespaceCommutativeRings.ParentMethods"
)
CATEGORY_SPECS_LIKE_BASE_DEPENDENT_PROVIDER = (
    f"{CATEGORY_SPECS_LIKE_PACKAGE}.namespace_subcategories."
    "commutative._BaseDependentConstruction.ParentMethods"
)


def test_resolver_writes_parent_projection_manifest_for_diamond_fixture(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "sage-category-projections.json"
    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "parent",
            *FIXTURE_CATEGORIES,
        ]
    )

    manifest = load_manifest(manifest_path)

    assert BOTTOM_PARENT_PROVIDER in manifest.projection_by_provider
    assert manifest.projection_by_provider[BOTTOM_PARENT_PROVIDER].role == "parent"
    assert manifest.source_module_by_module.keys() == {FIXTURE_MODULE}
    assert (
        manifest.source_module_by_module[FIXTURE_MODULE].path
        == "tests/fixtures/invariant_core/diamond_runtime.py"
    )


def test_resolver_manifest_round_trip_preserves_bottom_parent_mro(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sage-category-projections.json"
    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "parent",
            *FIXTURE_CATEGORIES,
        ]
    )
    round_trip_manifest = load_manifest(manifest_path)

    expected_projections = provider_projections_for_categories(
        FIXTURE_CATEGORIES,
        roles=("parent",),
    )
    expected_mro = expected_projections[BOTTOM_PARENT_PROVIDER].provider_mro

    assert (
        round_trip_manifest.projection_by_provider[BOTTOM_PARENT_PROVIDER].provider_mro
        == expected_mro
    )


def test_resolver_manifest_preserves_named_class_trace_records(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "sage-category-projections.json"
    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "parent",
            *FIXTURE_CATEGORIES,
        ]
    )
    manifest = load_manifest(manifest_path)
    projection = manifest.projection_by_provider[BOTTOM_PARENT_PROVIDER]
    trace = next(
        record
        for record in manifest.named_classes
        if record.provider == BOTTOM_PARENT_PROVIDER
    )

    assert trace.category == f"{FIXTURE_MODULE}.BottomCategory_with_category"
    assert trace.provider == BOTTOM_PARENT_PROVIDER
    assert trace.role == "parent"
    assert trace.trace_source == "Category._make_named_class"
    assert trace.runtime_class == projection.runtime_class
    assert trace.runtime_bases == projection.runtime_bases
    assert trace.runtime_mro == projection.runtime_mro
    assert trace.runtime_attr == "parent_class"
    assert trace.provider_attr == "ParentMethods"


def test_resolver_accepts_homset_provider_roles(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sage-category-homsets.json"
    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "homset_parent",
            HOMSET_BOTTOM_CATEGORY,
        ]
    )

    manifest = load_manifest(manifest_path)

    assert BOTTOM_HOMSET_PARENT_PROVIDER in manifest.projection_by_provider
    assert (
        manifest.projection_by_provider[BOTTOM_HOMSET_PARENT_PROVIDER].role
        == "homset_parent"
    )


def test_resolver_records_unsupported_shared_homset_provider(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "sage-category-unsupported-homset.json"

    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "homset_parent",
            SHARED_HOMSET_CATEGORY,
        ]
    )

    manifest = load_manifest(manifest_path)
    unsupported_provider = manifest.unsupported_provider_by_provider[
        SHARED_HOMSET_PROVIDER
    ]

    assert SHARED_HOMSET_PROVIDER not in manifest.projection_by_provider
    assert unsupported_provider.role == "homset_parent"
    assert unsupported_provider.reason == "ambiguous_runtime_mro"
    assert unsupported_provider.runtime_classes == (
        f"{HOMSET_FIXTURE_MODULE}.SharedStandaloneHomCategory.parent_class",
        f"{HOMSET_FIXTURE_MODULE}.SharedHomsetProviderCategory.Homsets.parent_class",
    )


def test_resolver_records_sage_git_revision_override(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sage-category-projections.json"
    sage_git_revision = "abc123abc123abc123abc123abc123abc123abcd"

    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "parent",
            "--sage-git-revision",
            sage_git_revision,
            *FIXTURE_CATEGORIES,
        ]
    )

    manifest = load_manifest(manifest_path)

    assert manifest.sage_git_revision == sage_git_revision


def test_resolver_records_projection_dependency_source_modules(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sage-category-axiom-projections.json"

    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "parent",
            COMMUTATIVE_RINGS_CATEGORY,
        ]
    )

    manifest = load_manifest(manifest_path)

    assert "sage.categories.commutative_rings" in manifest.source_module_by_module
    assert "sage.categories.rings" in manifest.source_module_by_module
    assert "sage.categories.magmas" in manifest.source_module_by_module
    assert "sage.categories.magmas.Magmas" not in manifest.source_module_by_module
    semirings_parent_class = "sage.categories.semirings.Semirings.parent_class"
    assert manifest.external_runtime_class_by_fullname[
        semirings_parent_class
    ].static_signature_source == "python_source"
    assert (
        manifest.external_runtime_class_by_fullname[semirings_parent_class].source_module
        == "sage.categories.semirings"
    )


def test_resolver_accepts_nested_axiom_category_fullname(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sage-category-nested-axiom-projections.json"

    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "parent",
            NESTED_AXIOM_CATEGORY,
        ]
    )

    manifest = load_manifest(manifest_path)
    projection = manifest.projection_by_provider[NESTED_AXIOM_PROVIDER]

    assert projection.provider_mro[:3] == (
        NESTED_AXIOM_PROVIDER,
        "sage.categories.finite_sets.FiniteSets.ParentMethods",
        AXIOM_ROOT_PROVIDER,
    )
    assert AXIOM_FIXTURE_MODULE in manifest.source_module_by_module
    assert (
        f"{AXIOM_FIXTURE_MODULE}.AxiomRootCategory"
        not in manifest.source_module_by_module
    )


def test_resolver_discovers_category_classes_from_package(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sage-category-package-projections.json"

    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "parent",
            "--package",
            CATEGORY_SPECS_LIKE_PACKAGE,
        ]
    )

    manifest = load_manifest(manifest_path)
    commutative_projection = manifest.projection_by_provider[
        CATEGORY_SPECS_LIKE_COMMUTATIVE_PROVIDER
    ]

    assert CATEGORY_SPECS_LIKE_ROOT_PROVIDER in manifest.projection_by_provider
    assert commutative_projection.provider_mro == (
        CATEGORY_SPECS_LIKE_COMMUTATIVE_PROVIDER,
        CATEGORY_SPECS_LIKE_ROOT_PROVIDER,
    )


def test_resolver_discovers_category_classes_in_namespace_subpackages(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "sage-category-namespace-package-projections.json"

    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "parent",
            "--package",
            CATEGORY_SPECS_LIKE_PACKAGE,
        ]
    )

    manifest = load_manifest(manifest_path)
    namespace_projection = manifest.projection_by_provider[
        CATEGORY_SPECS_LIKE_NAMESPACE_PROVIDER
    ]

    assert namespace_projection.provider_mro == (
        CATEGORY_SPECS_LIKE_NAMESPACE_PROVIDER,
        CATEGORY_SPECS_LIKE_ROOT_PROVIDER,
    )


def test_resolver_package_discovery_excludes_non_nullary_category_classes(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "sage-category-package-nullary-projections.json"

    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "parent",
            "--package",
            CATEGORY_SPECS_LIKE_PACKAGE,
        ]
    )

    manifest = load_manifest(manifest_path)

    assert CATEGORY_SPECS_LIKE_NAMESPACE_PROVIDER in manifest.projection_by_provider
    assert (
        CATEGORY_SPECS_LIKE_BASE_DEPENDENT_PROVIDER
        not in manifest.projection_by_provider
    )


def test_resolver_records_source_module_mtime_ns(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sage-category-axiom-projections.json"

    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "parent",
            *FIXTURE_CATEGORIES,
        ]
    )

    manifest = load_manifest(manifest_path)
    fixture_record = manifest.source_module_by_module[FIXTURE_MODULE]

    assert fixture_record.path == (
        "tests/fixtures/invariant_core/diamond_runtime.py"
    )
    assert fixture_record.mtime_ns == Path(fixture_record.path).stat().st_mtime_ns


def test_resolver_records_concrete_parent_initialization(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sage-category-concrete-parent-projections.json"

    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "parent",
            "--role",
            "element",
            "--concrete-parent",
            LEFT_ZERO_SEMIGROUP,
            SEMIGROUPS_CATEGORY,
        ]
    )

    manifest = load_manifest(manifest_path)
    record = manifest.concrete_parent_by_class[LEFT_ZERO_SEMIGROUP]

    assert record.runtime_class == (
        "sage.categories.examples.semigroups.LeftZeroSemigroup_with_category"
    )
    assert record.category_class == "sage.categories.semigroups.Semigroups_with_category"
    assert record.parent_provider_mro[0] == (
        "sage.categories.semigroups.Semigroups.ParentMethods"
    )
    assert record.element_provider_mro[0] == (
        "sage.categories.semigroups.Semigroups.ElementMethods"
    )
    assert manifest.external_runtime_class_by_fullname[
        "sage.structure.parent.Parent"
    ].static_signature_source == "untyped_external"
    assert record.parent_provider_mro[0] in manifest.projection_by_provider
    assert record.element_provider_mro[0] in manifest.projection_by_provider
    assert "sage.categories.examples.semigroups" in manifest.source_module_by_module


def test_resolver_records_parent_runtime_receiver_method(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sage-category-receiver-methods.json"

    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "parent",
            "--role",
            "element",
            "--concrete-parent",
            LEFT_ZERO_SEMIGROUP,
            SEMIGROUPS_CATEGORY,
        ]
    )

    manifest = load_manifest(manifest_path)

    assert (
        OBJECTS_PARENT_PROVIDER,
        "_an_element_",
        "object",
    ) in tuple(
        (record.provider, record.name, record.return_type)
        for record in manifest.provider_methods
    )


def test_resolver_records_self_return_provider_methods(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sage-category-self-methods.json"

    resolver.main(
        [
            "--output",
            str(manifest_path),
            "--role",
            "parent",
            SELF_RETURN_CATEGORY,
        ]
    )

    manifest = load_manifest(manifest_path)

    assert tuple(
        (record.provider, record.name, record.return_type)
        for record in manifest.provider_methods
    ) == ((SELF_RETURN_PROVIDER, "normalized", "Self"),)
