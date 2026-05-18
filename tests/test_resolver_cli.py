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
