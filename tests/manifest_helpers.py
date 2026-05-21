from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from sage_mypy_category_plugin.imports import importable_module_name_or_none
from sage_mypy_category_plugin.manifest import SourceModuleRecord
from sage_mypy_category_plugin.projection import (
    ExternalRuntimeClassRecord,
    ExternalRuntimeClassStaticSignatureSource,
    ProviderProjection,
)


def external_runtime_class_records_for_test_manifest(
    projections: Sequence[ProviderProjection],
    *,
    source_modules: Sequence[SourceModuleRecord] = (),
) -> tuple[ExternalRuntimeClassRecord, ...]:
    source_module_records = tuple(source_modules)
    return tuple(
        _external_runtime_class_record(
            runtime_class,
            source_modules=source_module_records,
        )
        for runtime_class in _unprojected_runtime_classes(projections)
    )


def _unprojected_runtime_classes(
    projections: Sequence[ProviderProjection],
) -> tuple[str, ...]:
    return tuple(
        runtime_class
        for runtime_class in dict.fromkeys(
            runtime_class
            for projection in projections
            for runtime_class in projection.unprojected_runtime_mro
        )
        if runtime_class != "builtins.object"
    )


def _external_runtime_class_record(
    runtime_class: str,
    *,
    source_modules: Sequence[SourceModuleRecord],
) -> ExternalRuntimeClassRecord:
    source_module = _source_module_for_fullname(
        runtime_class,
        source_modules=source_modules,
    )
    if source_module is not None:
        return ExternalRuntimeClassRecord(
            runtime_class=runtime_class,
            module=source_module.module,
            static_signature_source=_static_signature_source(source_module),
            source_module=source_module.module,
        )

    module_name = importable_module_name_or_none(runtime_class)
    assert module_name is not None, (
        f"test manifest must classify unprojected runtime class {runtime_class!r}"
    )
    return ExternalRuntimeClassRecord(
        runtime_class=runtime_class,
        module=module_name,
        static_signature_source="untyped_external",
    )


def _source_module_for_fullname(
    fullname: str,
    *,
    source_modules: Sequence[SourceModuleRecord],
) -> SourceModuleRecord | None:
    matching_records = tuple(
        record
        for record in source_modules
        if fullname == record.module or fullname.startswith(f"{record.module}.")
    )
    if not matching_records:
        return None
    return max(matching_records, key=lambda record: len(record.module))


def _static_signature_source(
    source_module: SourceModuleRecord,
) -> ExternalRuntimeClassStaticSignatureSource:
    suffix = Path(source_module.path).suffix
    if suffix == ".py":
        return "python_source"
    if suffix == ".pyi":
        return "stub"
    raise AssertionError(
        "test manifest source modules must be Python source or stub files: "
        f"{source_module.path!r}"
    )
