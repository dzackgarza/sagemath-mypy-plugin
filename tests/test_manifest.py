from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sage_mypy_category_plugin.manifest import (
    ProjectionManifest,
    load_manifest,
    write_manifest,
)
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
        sage_version="10.7",
        python_version="3.12.13",
        projections=(
            _base_projection(),
            _left_projection(),
            _right_projection(),
            _projection(),
        ),
    )
    return manifest.model_dump(mode="json")


def test_manifest_round_trips_projection_records(tmp_path: Path) -> None:
    manifest = ProjectionManifest.model_validate(_manifest_payload())
    manifest_path = tmp_path / "sage-category-projections.json"

    write_manifest(manifest_path, manifest)
    loaded = load_manifest(manifest_path)

    assert loaded == manifest
    assert loaded.projection_by_provider == {
        projection.provider: projection
        for projection in (
            _base_projection(),
            _left_projection(),
            _right_projection(),
            _projection(),
        )
    }


@pytest.mark.parametrize(
    ("mutation", "expected_field"),
    (
        ({"schema_version": 2}, "schema_version"),
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


def test_manifest_rejects_unresolved_provider_references() -> None:
    payload = _manifest_payload()
    payload["projections"] = [payload["projections"][-1]]

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert "unresolved provider reference" in str(raised.value)
