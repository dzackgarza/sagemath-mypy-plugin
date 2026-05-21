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
    NamedClassRecord,
    ProjectionManifest,
    SourceModuleRecord,
    UnsupportedProviderRecord,
    load_manifest,
    write_manifest,
)
from sage_mypy_category_plugin.projection import ConcreteParentRecord
from sage_mypy_category_plugin.projection import ExternalRuntimeClassRecord
from sage_mypy_category_plugin.projection import ProviderProjection
from sage_mypy_category_plugin.projection import roles_share_projection


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
            "runtime_bases": (
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.parent_class",
            ),
            "runtime_mro": (
                "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.parent_class",
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.parent_class",
                "builtins.object",
            ),
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
            "runtime_bases": (
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.parent_class",
            ),
            "runtime_mro": (
                "tests.fixtures.invariant_core.diamond_runtime.RightCategory.parent_class",
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.parent_class",
                "builtins.object",
            ),
            "provider_bases": (
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
            ),
            "provider_mro": (
                "tests.fixtures.invariant_core.diamond_runtime.RightCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
            ),
        }
    )


def _named_class_record() -> NamedClassRecord:
    return NamedClassRecord(
        category="tests.fixtures.invariant_core.diamond_runtime.BottomCategory_with_category",
        provider=(
            "tests.fixtures.invariant_core.diamond_runtime."
            "BottomCategory.ParentMethods"
        ),
        role="parent",
        trace_source="Category._make_named_class",
        runtime_class=(
            "tests.fixtures.invariant_core.diamond_runtime."
            "BottomCategory.parent_class"
        ),
        runtime_bases=(
            "tests.fixtures.invariant_core.diamond_runtime."
            "RightCategory.parent_class",
            "tests.fixtures.invariant_core.diamond_runtime."
            "LeftCategory.parent_class",
        ),
        runtime_mro=(
            "tests.fixtures.invariant_core.diamond_runtime."
            "BottomCategory.parent_class",
            "tests.fixtures.invariant_core.diamond_runtime."
            "RightCategory.parent_class",
            "tests.fixtures.invariant_core.diamond_runtime."
            "LeftCategory.parent_class",
            "tests.fixtures.invariant_core.diamond_runtime."
            "TopCategory.parent_class",
            "builtins.object",
        ),
        runtime_attr="parent_class",
        provider_attr="ParentMethods",
    )


def _unsupported_provider_record() -> UnsupportedProviderRecord:
    return UnsupportedProviderRecord(
        provider="tests.fixtures.invariant_core.diamond_runtime.SharedParentMethods",
        role="parent",
        reason="ambiguous_runtime_mro",
        runtime_classes=(
            "tests.fixtures.invariant_core.diamond_runtime."
            "SharedProviderTopCategory.parent_class",
            "tests.fixtures.invariant_core.diamond_runtime."
            "SharedProviderBottomCategory.parent_class",
        ),
        runtime_mros=(
            (
                "tests.fixtures.invariant_core.diamond_runtime."
                "SharedProviderTopCategory.parent_class",
                "builtins.object",
            ),
            (
                "tests.fixtures.invariant_core.diamond_runtime."
                "SharedProviderBottomCategory.parent_class",
                "tests.fixtures.invariant_core.diamond_runtime."
                "SharedProviderTopCategory.parent_class",
                "builtins.object",
            ),
        ),
    )


def _single_runtime_unsupported_provider_record() -> UnsupportedProviderRecord:
    return UnsupportedProviderRecord(
        provider="tests.fixtures.invariant_core.diamond_runtime.SharedParentMethods",
        role="parent",
        reason="ambiguous_runtime_mro",
        runtime_classes=(
            "tests.fixtures.invariant_core.diamond_runtime."
            "SharedProviderBottomCategory.parent_class",
        ),
        runtime_mros=(
            (
                "tests.fixtures.invariant_core.diamond_runtime."
                "SharedProviderBottomCategory.parent_class",
                "tests.fixtures.invariant_core.diamond_runtime."
                "SharedProviderTopCategory.parent_class",
                "builtins.object",
            ),
        ),
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
            SourceModuleRecord(
                module="sage.categories.examples.semigroups",
                path="sage/categories/examples/semigroups.py",
                sha256="0" * 64,
                mtime_ns=1_789_000_000_000_000_001,
            ),
            SourceModuleRecord(
                module="sage.categories.semigroups",
                path="sage/categories/semigroups.py",
                sha256="1" * 64,
                mtime_ns=1_789_000_000_000_000_002,
            ),
            SourceModuleRecord(
                module="sage.structure.parent",
                path="sage/structure/parent.pyx",
                sha256="2" * 64,
                mtime_ns=1_789_000_000_000_000_003,
            ),
            SourceModuleRecord(
                module="sage.structure.element",
                path="sage/structure/element.pyx",
                sha256="3" * 64,
                mtime_ns=1_789_000_000_000_000_004,
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
                element_runtime_mro=(
                    "sage.categories.examples.semigroups."
                    "LeftZeroSemigroup_with_category.element_class",
                    "sage.categories.examples.semigroups.LeftZeroSemigroup.Element",
                    "sage.structure.element.Element",
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
        ),
        "sage.categories.examples.semigroups": SourceModuleRecord(
            module="sage.categories.examples.semigroups",
            path="sage/categories/examples/semigroups.py",
            sha256="0" * 64,
            mtime_ns=1_789_000_000_000_000_001,
        ),
        "sage.categories.semigroups": SourceModuleRecord(
            module="sage.categories.semigroups",
            path="sage/categories/semigroups.py",
            sha256="1" * 64,
            mtime_ns=1_789_000_000_000_000_002,
        ),
        "sage.structure.parent": SourceModuleRecord(
            module="sage.structure.parent",
            path="sage/structure/parent.pyx",
            sha256="2" * 64,
            mtime_ns=1_789_000_000_000_000_003,
        ),
        "sage.structure.element": SourceModuleRecord(
            module="sage.structure.element",
            path="sage/structure/element.pyx",
            sha256="3" * 64,
            mtime_ns=1_789_000_000_000_000_004,
        ),
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


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("provider", "not a fullname"),
        ("runtime_class", "not a fullname"),
        ("runtime_bases", ("not a fullname",)),
        ("runtime_mro", ("not a fullname",)),
        ("provider_bases", ("not a fullname",)),
        ("provider_mro", ("not a fullname",)),
    ),
)
def test_manifest_rejects_malformed_projection_fullnames(
    field_name: str,
    value: str | tuple[str, ...],
) -> None:
    payload = _manifest_payload()
    payload["projections"] = [*payload["projections"]]
    payload["projections"][0] = {
        **payload["projections"][0],
        field_name: value,
    }

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert any(
        error["loc"][:3] == ("projections", 0, field_name)
        for error in raised.value.errors()
    )


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


def test_manifest_rejects_duplicate_provider_mro_entries() -> None:
    payload = _manifest_payload()
    payload["projections"] = [*payload["projections"]]
    provider_mro = payload["projections"][-1]["provider_mro"]
    payload["projections"][-1] = {
        **payload["projections"][-1],
        "provider_mro": (
            provider_mro[0],
            provider_mro[1],
            provider_mro[1],
            *provider_mro[2:],
        ),
    }

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert "duplicate provider_mro entries" in str(raised.value)


@pytest.mark.parametrize(
    ("projection_index", "mutation", "expected_field"),
    (
        (
            -1,
            {
                "provider_mro": (
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "RightCategory.ParentMethods",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "BottomCategory.ParentMethods",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "LeftCategory.ParentMethods",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "TopCategory.ParentMethods",
                )
            },
            "provider_mro",
        ),
        (
            -1,
            {
                "runtime_mro": (
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "RightCategory.parent_class",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "BottomCategory.parent_class",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "LeftCategory.parent_class",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "TopCategory.parent_class",
                    "builtins.object",
                )
            },
            "runtime_mro",
        ),
        (
            -1,
            {
                "provider_mro": (
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "BottomCategory.ParentMethods",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "LeftCategory.ParentMethods",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "TopCategory.ParentMethods",
                )
            },
            "provider_bases",
        ),
        (
            -1,
            {
                "runtime_mro": (
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "BottomCategory.parent_class",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "LeftCategory.parent_class",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "TopCategory.parent_class",
                    "builtins.object",
                )
            },
            "runtime_bases",
        ),
    ),
)
def test_manifest_rejects_projection_mro_inconsistency(
    projection_index: int,
    mutation: dict[str, Any],
    expected_field: str,
) -> None:
    payload = _manifest_payload()
    payload["projections"] = [*payload["projections"]]
    payload["projections"][projection_index] = {
        **payload["projections"][projection_index],
        **mutation,
    }

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    errors = raised.value.errors()
    assert {error["type"] for error in errors} == {"projection_graph_mismatch"}
    assert errors[0]["ctx"]["field"] == expected_field


def test_manifest_rejects_duplicate_source_module_records() -> None:
    payload = _manifest_payload()
    payload["source_modules"] = [
        payload["source_modules"][0],
        deepcopy(payload["source_modules"][0]),
    ]

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert "duplicate source module" in str(raised.value)


def test_manifest_rejects_duplicate_named_class_records() -> None:
    payload = _manifest_payload()
    named_class_record = _named_class_record().model_dump(mode="json")
    payload["named_classes"] = [named_class_record, deepcopy(named_class_record)]

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert "duplicate named class" in str(raised.value)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("category", "not a fullname"),
        ("provider", "not a fullname"),
        ("runtime_class", "not a fullname"),
        ("runtime_bases", ("not a fullname",)),
        ("runtime_mro", ("not a fullname",)),
    ),
)
def test_manifest_rejects_malformed_named_class_fullnames(
    field_name: str,
    value: str | tuple[str, ...],
) -> None:
    payload = _manifest_payload()
    named_class_record = _named_class_record().model_dump(mode="json")
    named_class_record[field_name] = value
    payload["named_classes"] = [named_class_record]

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert any(
        error["loc"][:3] == ("named_classes", 0, field_name)
        for error in raised.value.errors()
    )


def test_manifest_accepts_named_class_trace_role_alias_when_projection_matches() -> None:
    payload = _manifest_payload()
    named_class_record = _named_class_record().model_dump(mode="json")
    named_class_record["role"] = "homset_parent"
    payload["named_classes"] = [named_class_record]

    manifest = ProjectionManifest.model_validate(payload)

    assert manifest.named_classes[0].role == "homset_parent"


def test_manifest_records_unsupported_provider_classification() -> None:
    payload = _manifest_payload()
    unsupported_record = _unsupported_provider_record()
    payload["unsupported_providers"] = [unsupported_record.model_dump(mode="json")]

    manifest = ProjectionManifest.model_validate(payload)

    assert manifest.unsupported_provider_by_provider == {
        unsupported_record.provider: unsupported_record
    }
    assert unsupported_record.provider not in manifest.projection_by_provider


def test_manifest_allows_supported_projection_to_reference_unsupported_provider() -> None:
    payload = _manifest_payload()
    unsupported_record = _unsupported_provider_record()
    dependent_provider = (
        "tests.fixtures.invariant_core.diamond_runtime."
        "DependentSharedProviderCategory.ParentMethods"
    )
    dependent_runtime_class = (
        "tests.fixtures.invariant_core.diamond_runtime."
        "DependentSharedProviderCategory.parent_class"
    )
    dependent_projection = _projection().model_copy(
        update={
            "provider": dependent_provider,
            "runtime_class": dependent_runtime_class,
            "runtime_bases": (unsupported_record.runtime_classes[1],),
            "runtime_mro": (
                dependent_runtime_class,
                *unsupported_record.runtime_mros[1],
            ),
            "provider_bases": (unsupported_record.provider,),
            "provider_mro": (dependent_provider, unsupported_record.provider),
        }
    )
    payload["projections"] = [dependent_projection.model_dump(mode="json")]
    payload["unsupported_providers"] = [unsupported_record.model_dump(mode="json")]
    payload["concrete_parents"] = []

    manifest = ProjectionManifest.model_validate(payload)

    assert manifest.projections == (dependent_projection,)
    assert manifest.unsupported_providers == (unsupported_record,)


def test_manifest_allows_supported_projection_to_reference_single_runtime_unsupported_provider() -> None:
    payload = _manifest_payload()
    unsupported_record = _single_runtime_unsupported_provider_record()
    dependent_provider = (
        "tests.fixtures.invariant_core.diamond_runtime."
        "DependentSharedProviderCategory.ParentMethods"
    )
    dependent_runtime_class = (
        "tests.fixtures.invariant_core.diamond_runtime."
        "DependentSharedProviderCategory.parent_class"
    )
    dependent_projection = _projection().model_copy(
        update={
            "provider": dependent_provider,
            "runtime_class": dependent_runtime_class,
            "runtime_bases": unsupported_record.runtime_classes,
            "runtime_mro": (
                dependent_runtime_class,
                *unsupported_record.runtime_mros[0],
            ),
            "provider_bases": (unsupported_record.provider,),
            "provider_mro": (dependent_provider, unsupported_record.provider),
        }
    )
    payload["projections"] = [dependent_projection.model_dump(mode="json")]
    payload["unsupported_providers"] = [unsupported_record.model_dump(mode="json")]
    payload["concrete_parents"] = []

    manifest = ProjectionManifest.model_validate(payload)

    assert manifest.projections == (dependent_projection,)
    assert manifest.unsupported_providers == (unsupported_record,)


def test_manifest_keeps_role_distinct_unsupported_provider_records() -> None:
    payload = _manifest_payload()
    parent_record = _unsupported_provider_record()
    homset_record = parent_record.model_copy(update={"role": "homset_parent"})
    payload["unsupported_providers"] = [
        parent_record.model_dump(mode="json"),
        homset_record.model_dump(mode="json"),
    ]

    manifest = ProjectionManifest.model_validate(payload)

    assert manifest.unsupported_provider_by_role_and_provider == {
        ("parent", parent_record.provider): parent_record,
        ("homset_parent", homset_record.provider): homset_record,
    }
    with pytest.raises(ValueError):
        manifest.unsupported_provider_by_provider


def test_manifest_rejects_supported_and_unsupported_provider_overlap() -> None:
    payload = _manifest_payload()
    unsupported_record = _unsupported_provider_record().model_copy(
        update={
            "provider": _projection().provider,
        }
    )
    payload["unsupported_providers"] = [unsupported_record.model_dump(mode="json")]

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    errors = raised.value.errors()
    assert {error["type"] for error in errors} == {
        "unsupported_provider_projection_overlap"
    }
    assert errors[0]["ctx"] == {
        "provider": _projection().provider,
        "role": "parent",
    }


@pytest.mark.parametrize(
    ("mutation", "expected_field"),
    (
        (
            {
                "runtime_classes": (),
            },
            "runtime_classes",
        ),
        (
            {
                "runtime_mros": (
                    (
                        "tests.fixtures.invariant_core.diamond_runtime."
                        "SharedProviderTopCategory.parent_class",
                        "builtins.object",
                    ),
                )
            },
            "runtime_mros",
        ),
        (
            {
                "runtime_classes": (
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "SharedProviderTopCategory.parent_class",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "SharedProviderTopCategory.parent_class",
                )
            },
            "runtime_classes",
        ),
        (
            {
                "runtime_mros": (
                    (
                        "builtins.object",
                        "tests.fixtures.invariant_core.diamond_runtime."
                        "SharedProviderTopCategory.parent_class",
                    ),
                    (
                        "tests.fixtures.invariant_core.diamond_runtime."
                        "SharedProviderBottomCategory.parent_class",
                        "builtins.object",
                    ),
                )
            },
            "runtime_mros",
        ),
    ),
)
def test_manifest_rejects_incoherent_unsupported_provider_evidence(
    mutation: dict[str, Any],
    expected_field: str,
) -> None:
    unsupported_record = _unsupported_provider_record().model_dump(mode="json")
    unsupported_record.update(mutation)

    with pytest.raises(ValidationError) as raised:
        UnsupportedProviderRecord.model_validate(unsupported_record)

    errors = raised.value.errors()
    assert {error["type"] for error in errors} == {
        "unsupported_provider_graph_mismatch"
    }
    assert errors[0]["ctx"]["field"] == expected_field


def test_manifest_semantic_digest_tracks_unsupported_provider_changes() -> None:
    payload = _manifest_payload()
    unsupported_record = _unsupported_provider_record()
    payload["unsupported_providers"] = [unsupported_record.model_dump(mode="json")]
    base_manifest = ProjectionManifest.model_validate(payload)

    mutated_payload = base_manifest.model_dump(mode="json")
    mutated_payload["unsupported_providers"][0]["runtime_mros"] = (
        unsupported_record.runtime_mros[0],
        (
            "tests.fixtures.invariant_core.diamond_runtime."
            "SharedProviderBottomCategory.parent_class",
            "builtins.object",
        ),
    )
    mutated_manifest = ProjectionManifest.model_validate(mutated_payload)

    assert (
        base_manifest.semantic_projection_digest
        != mutated_manifest.semantic_projection_digest
    )


@pytest.mark.parametrize(
    ("mutation", "expected_field"),
    (
        ({"role": "element"}, "role"),
        (
            {
                "runtime_class": (
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "TopCategory.parent_class"
                )
            },
            "runtime_class",
        ),
        (
            {
                "runtime_bases": (
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "LeftCategory.parent_class",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "RightCategory.parent_class",
                )
            },
            "runtime_bases",
        ),
        (
            {
                "runtime_mro": (
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "BottomCategory.parent_class",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "LeftCategory.parent_class",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "RightCategory.parent_class",
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "TopCategory.parent_class",
                    "builtins.object",
                )
            },
            "runtime_mro",
        ),
    ),
)
def test_manifest_rejects_named_class_trace_projection_mismatch(
    mutation: dict[str, Any],
    expected_field: str,
) -> None:
    payload = _manifest_payload()
    named_class_record = _named_class_record().model_dump(mode="json")
    named_class_record.update(mutation)
    payload["named_classes"] = [named_class_record]

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    errors = raised.value.errors()
    assert {error["type"] for error in errors} == {
        "named_class_projection_mismatch"
    }
    assert errors[0]["ctx"]["field"] == expected_field


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


def test_manifest_requires_external_metadata_for_unprojected_runtime_classes() -> None:
    payload = _manifest_payload()
    payload["projections"] = [*payload["projections"]]
    payload["projections"][0] = {
        **payload["projections"][0],
        "unprojected_runtime_mro": ("sage.structure.parent.Parent",),
    }

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    errors = raised.value.errors()
    assert {error["type"] for error in errors} == {
        "external_runtime_class_missing"
    }
    assert errors[0]["ctx"]["runtime_class"] == "sage.structure.parent.Parent"


def test_manifest_records_external_runtime_class_boundaries() -> None:
    payload = _manifest_payload()
    payload["projections"] = [*payload["projections"]]
    payload["projections"][0] = {
        **payload["projections"][0],
        "unprojected_runtime_mro": ("sage.structure.parent.Parent",),
    }
    payload["external_runtime_classes"] = [
        {
            "runtime_class": "sage.structure.parent.Parent",
            "module": "sage.structure.parent",
            "static_signature_source": "untyped_external",
            "source_module": None,
        }
    ]

    manifest = ProjectionManifest.model_validate(payload)

    assert manifest.model_dump(mode="json")["external_runtime_classes"] == (
        payload["external_runtime_classes"]
    )
    assert manifest.external_runtime_class_by_fullname[
        "sage.structure.parent.Parent"
    ].static_signature_source == "untyped_external"


def test_manifest_semantic_digest_tracks_external_runtime_class_boundaries() -> None:
    payload = _manifest_payload()
    payload["projections"] = [*payload["projections"]]
    payload["projections"][0] = {
        **payload["projections"][0],
        "unprojected_runtime_mro": ("sage.structure.parent.Parent",),
    }
    payload["external_runtime_classes"] = [
        {
            "runtime_class": "sage.structure.parent.Parent",
            "module": "sage.structure.parent",
            "static_signature_source": "untyped_external",
            "source_module": None,
        }
    ]
    untyped_manifest = ProjectionManifest.model_validate(payload)
    payload["external_runtime_classes"][0] = {
        **payload["external_runtime_classes"][0],
        "static_signature_source": "stub",
        "source_module": "sage.structure.parent",
    }
    stub_visible_manifest = ProjectionManifest.model_validate(payload)

    assert (
        untyped_manifest.semantic_projection_digest
        != stub_visible_manifest.semantic_projection_digest
    )


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


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("concrete_class", "not a fullname"),
        ("runtime_class", "not a fullname"),
        ("runtime_mro", ("not a fullname",)),
        ("category_class", "not a fullname"),
        ("parent_provider_mro", ("not a fullname",)),
        ("element_runtime_class", "not a fullname"),
        ("element_provider_mro", ("not a fullname",)),
    ),
)
def test_manifest_rejects_malformed_concrete_parent_fullnames(
    field_name: str,
    value: str | tuple[str, ...],
) -> None:
    payload = _manifest_payload()
    payload["concrete_parents"] = [*payload["concrete_parents"]]
    payload["concrete_parents"][0] = {
        **payload["concrete_parents"][0],
        field_name: value,
    }

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert any(
        error["loc"][:3] == ("concrete_parents", 0, field_name)
        for error in raised.value.errors()
    )


@pytest.mark.parametrize(
    ("mutation", "expected_field"),
    (
        (
            {
                "runtime_mro": (
                    "sage.categories.examples.semigroups.LeftZeroSemigroup",
                    "sage.categories.examples.semigroups."
                    "LeftZeroSemigroup_with_category",
                    "sage.structure.parent.Parent",
                )
            },
            "runtime_mro",
        ),
        ({"parent_provider_mro": ()}, "parent_provider_mro"),
        (
            {
                "element_runtime_class": (
                    "sage.categories.examples.semigroups."
                    "LeftZeroSemigroup_with_category.element_class"
                ),
                "element_provider_mro": (),
            },
            "element_provider_mro",
        ),
        (
            {
                "element_runtime_class": None,
                "element_provider_mro": (
                    "tests.fixtures.invariant_core.diamond_runtime."
                    "TopCategory.ElementMethods",
                ),
            },
            "element_runtime_class",
        ),
    ),
)
def test_manifest_rejects_incoherent_concrete_parent_records(
    mutation: dict[str, Any],
    expected_field: str,
) -> None:
    payload = _manifest_payload()
    payload["concrete_parents"] = [
        {
            **payload["concrete_parents"][0],
            **mutation,
        }
    ]

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    errors = raised.value.errors()
    assert {error["type"] for error in errors} == {"concrete_parent_graph_mismatch"}
    assert errors[0]["ctx"]["field"] == expected_field


@pytest.mark.parametrize(
    "missing_module",
    (
        "tests.fixtures.invariant_core.diamond_runtime",
        "sage.categories.examples.semigroups",
        "sage.structure.parent",
    ),
)
def test_manifest_rejects_source_backed_symbols_without_module_coverage(
    missing_module: str,
) -> None:
    payload = _manifest_payload()
    payload["source_modules"] = [
        source_module
        for source_module in payload["source_modules"]
        if source_module["module"] != missing_module
    ]

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert {error["type"] for error in raised.value.errors()} == {
        "source_module_coverage"
    }


def test_manifest_rejects_malformed_source_module_name() -> None:
    payload = _manifest_payload()
    payload["source_modules"][0]["module"] = "not a module"

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert any(
        error["loc"] == ("source_modules", 0, "module")
        for error in raised.value.errors()
    )


def test_manifest_rejects_malformed_provider_method_provider_fullname() -> None:
    payload = _manifest_payload()
    payload["provider_methods"] = [
        {
            "provider": "not a fullname",
            "name": "normalized",
            "return_type": "Self",
        }
    ]

    with pytest.raises(ValidationError) as raised:
        ProjectionManifest.model_validate(payload)

    assert any(
        error["loc"] == ("provider_methods", 0, "provider")
        for error in raised.value.errors()
    )


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


def test_manifest_semantic_digest_tracks_concrete_element_runtime_mro() -> None:
    base_manifest = ProjectionManifest.model_validate(_manifest_payload())
    mutated_payload = base_manifest.model_dump(mode="json")
    mutated_payload["concrete_parents"][0]["element_runtime_mro"] = (
        "sage.categories.examples.semigroups.LeftZeroSemigroup_with_category."
        "element_class",
        "sage.categories.examples.semigroups.LeftZeroSemigroup.Element",
    )
    mutated_manifest = ProjectionManifest.model_validate(mutated_payload)

    assert base_manifest.semantic_projection_digest != (
        mutated_manifest.semantic_projection_digest
    )


def test_manifest_semantic_digest_tracks_named_class_trace_changes() -> None:
    base_payload = _manifest_payload()
    base_payload["named_classes"] = [_named_class_record().model_dump(mode="json")]
    base_manifest = ProjectionManifest.model_validate(base_payload)
    mutated_payload = base_manifest.model_dump(mode="json")
    mutated_payload["named_classes"][0]["runtime_attr"] = "element_class"
    mutated_manifest = ProjectionManifest.model_validate(mutated_payload)

    assert base_manifest.semantic_projection_digest != (
        mutated_manifest.semantic_projection_digest
    )


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


def test_external_runtime_class_record_rejects_untyped_with_source_module() -> None:
    """ExternalRuntimeClassRecord must reject untyped_external + source_module combination.

    An untyped_external class has no source module — it is represented in stubs
    by a shelled-out empty class stub (class Parent: ...).  Claiming a source_module
    on an untyped_external record would be contradictory: the stubs.py generator
    would treat the class as python_source-visible and skip generating the shell,
    leaving mypy with no definition for the class.
    """
    with pytest.raises(ValidationError) as raised:
        ExternalRuntimeClassRecord(
            runtime_class="sage.structure.parent.Parent",
            module="sage.structure.parent",
            static_signature_source="untyped_external",
            source_module="sage.structure.parent",
        )

    assert any(
        "untyped external runtime classes must not claim a source module" in str(e["msg"])
        for e in raised.value.errors()
    )


def test_external_runtime_class_record_rejects_python_source_without_source_module() -> None:
    """ExternalRuntimeClassRecord must reject python_source + missing source_module.

    A python_source class claims that mypy can read its type information from
    Python source.  Without a source_module, the stubs.py generator cannot
    record which module's source file carries the class, so the preserved-source
    metadata is incomplete.  stub and python_source are treated identically
    for this requirement: both must name their source_module.
    """
    for signature_source in ("python_source", "stub"):
        with pytest.raises(ValidationError) as raised:
            ExternalRuntimeClassRecord(
                runtime_class="sage.categories.sets_cat.Sets.parent_class",
                module="sage.categories.sets_cat",
                static_signature_source=signature_source,  # type: ignore[arg-type]
                source_module=None,
            )

        assert any(
            "source_module" in str(e["msg"])
            for e in raised.value.errors()
        ), f"Expected source_module error for {signature_source!r}"


def test_roles_share_projection_encodes_role_alias_semantics() -> None:
    """roles_share_projection() must reflect the ROLE_PROJECTION_ALIASES contract.

    This function gates deduplication in the resolver, named-class trace validation
    in the manifest, and provider-MRO sharing in the oracle.  The alias pairs
    (parent↔homset_parent, element↔homset_element) mean these roles share the same
    runtime named-class — Sage creates a single parent_class / element_class for
    both normal and homset variants.  Non-alias pairs must NOT share projection or
    deduplication would incorrectly merge distinct roles.
    """
    # Every role shares projection with itself (reflexivity)
    for role in ("parent", "element", "subcategory", "morphism", "homset_parent", "homset_element"):
        assert roles_share_projection(role, role), (  # type: ignore[arg-type]
            f"{role!r} must share projection with itself"
        )

    # The two approved alias pairs: Sage creates one named class for both
    assert roles_share_projection("parent", "homset_parent")
    assert roles_share_projection("homset_parent", "parent")
    assert roles_share_projection("element", "homset_element")
    assert roles_share_projection("homset_element", "element")

    # Unrelated pairs must NOT share projection — different runtime named classes
    assert not roles_share_projection("parent", "element")
    assert not roles_share_projection("parent", "subcategory")
    assert not roles_share_projection("parent", "morphism")
    assert not roles_share_projection("parent", "homset_element")
    assert not roles_share_projection("element", "subcategory")
    assert not roles_share_projection("element", "morphism")
    assert not roles_share_projection("element", "homset_parent")
    assert not roles_share_projection("homset_parent", "homset_element")
    assert not roles_share_projection("subcategory", "morphism")
