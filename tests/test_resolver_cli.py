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
COMMUTATIVE_RINGS_CATEGORY = "sage.categories.commutative_rings.CommutativeRings"
SEMIGROUPS_CATEGORY = "sage.categories.semigroups.Semigroups"
LEFT_ZERO_SEMIGROUP = "sage.categories.examples.semigroups.LeftZeroSemigroup"


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
    assert record.parent_provider_mro[0] in manifest.projection_by_provider
    assert record.element_provider_mro[0] in manifest.projection_by_provider
    assert "sage.categories.examples.semigroups" in manifest.source_module_by_module
