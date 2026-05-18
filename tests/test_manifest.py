from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from mypy.version import __version__ as MYPY_VERSION
from packaging.version import Version
import pytest
from pydantic import ValidationError

from sage_mypy_category_plugin.manifest import (
    CURRENT_PLUGIN_SCHEMA_VERSION,
    ProjectionManifest,
    SourceModuleRecord,
    load_manifest,
    write_manifest,
)
from sage_mypy_category_plugin.projection import ConcreteParentRecord
from sage_mypy_category_plugin.projection import ProviderProjection


def _projection() -> ProviderProjection:
    return ProviderProjection(
        provider="tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods",
        role="parent",
        runtime_class="tests.fixtures.invariant_core.diamond_runtime.BottomCategory.parent_class",
        runtime_bases=(
            "tests.fixtures.invariant_core.diamond_runtime.RightCategory.parent_class",
            "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.parent_class",
        ),
        runtime_mro=(
            "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.parent_class",
            "tests.fixtures.invariant_core.diamond_runtime.RightCategory.parent_class",
            "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.parent_class",
            "tests.fixtures.invariant_core.diamond_runtime.TopCategory.parent_class",
            "builtins.object",
        ),
        provider_bases=(
            "tests.fixtures.invariant_core.diamond_runtime.RightCategory.ParentMethods",
            "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.ParentMethods",
        ),
        provider_mro=(
            "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods",
            "tests.fixtures.invariant_core.diamond_runtime.RightCategory.ParentMethods",
            "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.ParentMethods",
            "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
        ),
    )


def _base_projection() -> ProviderProjection:
    return _projection().model_copy(
        update={
            "provider": "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
            "runtime_class": "tests.fixtures.invariant_core.diamond_runtime.TopCategory.parent_class",
            "runtime_bases": ("builtins.object",),
            "runtime_mro": (
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.parent_class",
                "builtins.object",
            ),
            "provider_bases": (),
            "provider_mro": (
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
            ),
        }
    )


def _base_element_projection() -> ProviderProjection:
    return _projection().model_copy(
        update={
            "provider": "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ElementMethods",
            "role": "element",
            "runtime_class": "tests.fixtures.invariant_core.diamond_runtime.TopCategory.element_class",
            "runtime_bases": ("builtins.object",),
            "runtime_mro": (
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.element_class",
                "builtins.object",
            ),
            "provider_bases": (),
            "provider_mro": (
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ElementMethods",
            ),
        }
    )


def _left_projection() -> ProviderProjection:
    return _projection().model_copy(
        update={
            "provider": "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.ParentMethods",
            "runtime_class": "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.parent_class",
            "provider_bases": (
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
            ),
            "provider_mro": (
                "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
            ),
        }
    )


def _right_projection() -> ProviderProjection:
    return _projection().model_copy(
        update={
            "provider": "tests.fixtures.invariant_core.diamond_runtime.RightCategory.ParentMethods",
            "runtime_class": "tests.fixtures.invariant_core.diamond_runtime.RightCategory.parent_class",
            "provider_bases": (
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
            ),
            "provider_mro": (
                "tests.fixtures.invariant_core.diamond_runtime.RightCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
            ),
        }
    )


def _manifest_payload() -> dict[str, Any]:
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        plugin_schema_version=CURRENT_PLUGIN_SCHEMA_VERSION,
        sage_version="10.7",
        sage_git_revision="abc123abc123abc123abc123abc123abc123abcd",
        python_version="3.12.13",
        mypy_min_version=MYPY_VERSION,
        mypy_max_version=MYPY_VERSION,
        projections=(
            _base_projection(),
            _base_element_projection(),
            _left_projection(),
            _right_projection(),
            _projection(),
        ),
        source_modules=(
            SourceModuleRecord(
                module="tests.fixtures.invariant_core.diamond_runtime",
                path="tests/fixtures/invariant_core/diamond_runtime.py",
                sha256="9f1f7a4a0d0b6dfd7f9d2d2c1d3b5e6a"
                "8b1c0f7a6d5e4c3b2a19080706050403",
                mtime_ns=1_789_000_000_000_000_000,
            ),
        ),
        concrete_parents=(
            ConcreteParentRecord(
                concrete_class="sage.categories.examples.semigroups.LeftZeroSemigroup",
                runtime_class=(
                    "sage.categories.examples.semigroups."
                    "LeftZeroSemigroup_with_category"
                ),
                runtime_mro=(
                    "sage.categories.examples.semigroups."
                    "LeftZeroSemigroup_with_category",
                    "sage.categories.examples.semigroups.LeftZeroSemigroup",
                    "sage.structure.parent.Parent",
                ),
                category_class="sage.categories.semigroups.Semigroups_with_category",
                parent_provider_mro=(
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "TopCategory.ParentMethods",
                ),
                element_runtime_class=(
                    "sage.categories.examples.semigroups."
                    "LeftZeroSemigroup_with_category.element_class"
                ),
                element_provider_mro=(
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "TopCategory.ElementMethods",
                ),
            ),
        ),
    )
    return manifest.model_dump(mode="json")


def test_manifest_round_trips_projection_records(tmp_path: Path) -> None:
    manifest = ProjectionManifest.model_validate(_manifest_payload())
    manifest_path = tmp_path / "sage-category-projections.json"

    write_manifest(manifest_path, manifest)
    loaded = load_manifest(manifest_path)

    assert loaded == manifest
    assert loaded.plugin_schema_version == CURRENT_PLUGIN_SCHEMA_VERSION
    assert loaded.mypy_min_version == MYPY_VERSION
    assert loaded.mypy_max_version == MYPY_VERSION
    assert loaded.projection_by_provider == {
        projection.provider: projection
        for projection in (
            _base_projection(),
            _base_element_projection(),
            _left_projection(),
            _right_projection(),
            _projection(),
        )
    }
    assert loaded.source_module_by_module == {
        "tests.fixtures.invariant_core.diamond_runtime": SourceModuleRecord(
            module="tests.fixtures.invariant_core.diamond_runtime",
            path="tests/fixtures/invariant_core/diamond_runtime.py",
            sha256="9f1f7a4a0d0b6dfd7f9d2d2c1d3b5e6a"
            "8b1c0f7a6d5e4c3b2a19080706050403",
            mtime_ns=1_789_000_000_000_000_000,
        )
    }
    assert loaded.concrete_parent_by_class == {
        record.concrete_class: record
        for record in loaded.concrete_parents
    }


@pytest.mark.parametrize(
    ("mutation", "expected_field"),
    (
        ({"schema_version": 2}, "schema_version"),
        ({"plugin_schema_version": "2"}, "plugin_schema_version"),
        (
            {
                "mypy_min_version": str(Version(MYPY_VERSION).release[0] + 1),
                "mypy_max_version": str(Version(MYPY_VERSION).release[0] + 1),
            },
            "mypy",
        ),
        ({"projections": None}, "projections"),
        ({"projections": [{"provider": 17}]}, "provider"),
        ({"projections": [{"provider_mro": "not-a-list"}]}, "provider_mro"),
    ),
)
def test_manifest_rejects_malformed_projection_data(
    mutation: dict[str, Any],
    expected_field: str,
) -> None:
    payload = _manifest_payload()
    if "projections" in mutation and isinstance(mutation["projections"], list):
        payload["projections"] = [deepcopy(payload["projections"][0])]
        payload["projections"][0].update(mutation["projections"][0])
    else:
        payload.update(mutation)

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert expected_field in str(raised.value)


def test_manifest_rejects_missing_required_fields() -> None:
    payload = _manifest_payload()
    del payload["generated_by"]

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert "generated_by" in str(raised.value)


def test_manifest_rejects_duplicate_provider_records() -> None:
    payload = _manifest_payload()
    payload["projections"] = [
        payload["projections"][0],
        deepcopy(payload["projections"][0]),
    ]

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert "duplicate provider" in str(raised.value)


def test_manifest_rejects_duplicate_source_module_records() -> None:
    payload = _manifest_payload()
    payload["source_modules"] = [
        payload["source_modules"][0],
        deepcopy(payload["source_modules"][0]),
    ]

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert "duplicate source module" in str(raised.value)


def test_manifest_rejects_malformed_source_module_hash() -> None:
    payload = _manifest_payload()
    payload["source_modules"][0]["sha256"] = "not-a-sha256"

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert "sha256" in str(raised.value)


def test_manifest_rejects_negative_source_module_mtime() -> None:
    payload = _manifest_payload()
    payload["source_modules"][0]["mtime_ns"] = -1

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert "mtime_ns" in str(raised.value)


def test_manifest_rejects_invalid_sage_git_revision() -> None:
    payload = _manifest_payload()
    payload["sage_git_revision"] = "not-a-revision"

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert "sage_git_revision" in str(raised.value)


def test_manifest_rejects_unresolved_provider_references() -> None:
    payload = _manifest_payload()
    payload["projections"] = [payload["projections"][-1]]

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert "unresolved provider reference" in str(raised.value)


def test_manifest_rejects_unresolved_concrete_parent_provider_references() -> None:
    payload = _manifest_payload()
    payload["concrete_parents"][0]["element_provider_mro"] = [
        "tests.fixtures.invariant_core.diamond_runtime.MissingCategory.ElementMethods"
    ]

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert "unresolved provider reference" in str(raised.value)


def test_manifest_semantic_digest_is_deterministic_for_equivalent_content() -> None:
    manifest_payload = _manifest_payload()
    shuffled_payload = {
        key: manifest_payload[key]
        for key in reversed(tuple(manifest_payload))
    }
    manifest_a = ProjectionManifest.model_validate(manifest_payload)
    manifest_b = ProjectionManifest.model_validate(shuffled_payload)

    assert manifest_a.semantic_projection_digest == manifest_b.semantic_projection_digest


def test_manifest_semantic_digest_tracks_projection_changes() -> None:
    base_manifest = ProjectionManifest.model_validate(_manifest_payload())
    mutated_payload = base_manifest.model_dump(mode="json")
    mutated_payload["projections"] = [*mutated_payload["projections"]]

    projection_to_mutate = next(
        projection
        for projection in mutated_payload["projections"]
        if len(projection["provider_mro"]) >= 3
    )
    first_projection_mro = list(projection_to_mutate["provider_mro"])
    first_projection_mro[1], first_projection_mro[2] = (
        first_projection_mro[2],
        first_projection_mro[1],
    )
    projection_to_mutate["provider_mro"] = tuple(first_projection_mro)
    mutated_manifest = ProjectionManifest.model_validate(mutated_payload)

    assert base_manifest.semantic_projection_digest != mutated_manifest.semantic_projection_digest


def test_manifest_source_module_digest_tracks_source_hash_changes() -> None:
    base_manifest = ProjectionManifest.model_validate(_manifest_payload())
    mutated_payload = base_manifest.model_dump(mode="json")
    source_record = mutated_payload["source_modules"][0]
    source_record["sha256"] = (
        "0f1f7a4a0d0b6dfd7f9d2d2c1d3b5e6a"
        "8b1c0f7a6d5e4c3b2a19080706050403"
    )
    mutated_manifest = ProjectionManifest.model_validate(mutated_payload)

    assert base_manifest.source_module_digest != mutated_manifest.source_module_digest


def test_manifest_source_module_digest_tracks_source_mtime_changes() -> None:
    base_manifest = ProjectionManifest.model_validate(_manifest_payload())
    mutated_payload = base_manifest.model_dump(mode="json")
    mutated_payload["source_modules"][0]["mtime_ns"] += 1
    mutated_manifest = ProjectionManifest.model_validate(mutated_payload)

    assert base_manifest.source_module_digest != mutated_manifest.source_module_digest
