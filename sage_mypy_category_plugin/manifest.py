from __future__ import annotations

import json
from hashlib import sha256
import re

from pathlib import Path
from typing import Literal, Self

from mypy.version import __version__ as MYPY_VERSION
from packaging.version import Version
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr, model_validator
from pydantic_core import PydanticCustomError

from sage_mypy_category_plugin.projection import (
    ConcreteParentRecord,
    ProviderProjection,
    ProviderRole,
)

CURRENT_PLUGIN_SCHEMA_VERSION = "1"
SHA256_HEX_PATTERN = re.compile(r"[0-9a-f]{64}")
GIT_REVISION_PATTERN = re.compile(r"[0-9a-f]{40}")
INTRINSIC_MODULES = frozenset(("builtins",))


class SourceModuleRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    module: StrictStr
    path: StrictStr
    sha256: StrictStr
    mtime_ns: StrictInt

    @model_validator(mode="after")
    def _validate_source_metadata(self) -> Self:
        if SHA256_HEX_PATTERN.fullmatch(self.sha256) is None:
            raise ValueError(
                "sha256 must be 64 lowercase hex characters: "
                f"{self.sha256!r}"
            )
        if self.mtime_ns < 0:
            raise ValueError(f"mtime_ns must be nonnegative: {self.mtime_ns!r}")
        return self


class NamedClassRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    category: StrictStr
    provider: StrictStr
    role: ProviderRole
    trace_source: StrictStr
    runtime_class: StrictStr
    runtime_bases: tuple[StrictStr, ...]
    runtime_mro: tuple[StrictStr, ...]
    runtime_attr: StrictStr
    provider_attr: StrictStr


class ProjectionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    generated_by: StrictStr
    plugin_schema_version: Literal["1"] = CURRENT_PLUGIN_SCHEMA_VERSION
    sage_version: StrictStr
    sage_git_revision: StrictStr | None = None
    mypy_min_version: StrictStr = "0.0.0"
    mypy_max_version: StrictStr = "9999.9999.9999"
    python_version: StrictStr
    named_classes: tuple[NamedClassRecord, ...] = ()
    projections: tuple[ProviderProjection, ...]
    source_modules: tuple[SourceModuleRecord, ...] = ()
    concrete_parents: tuple[ConcreteParentRecord, ...] = ()

    @model_validator(mode="after")
    def _validate_git_revision(self) -> Self:
        if self.sage_git_revision is not None:
            if not GIT_REVISION_PATTERN.fullmatch(self.sage_git_revision):
                raise ValueError(
                    "sage_git_revision must be 40 lowercase hex characters: "
                    f"{self.sage_git_revision!r}"
                )
        return self

    @model_validator(mode="after")
    def _validate_projection_graph(self) -> Self:
        providers = tuple(projection.provider for projection in self.projections)
        duplicate_providers = tuple(
            provider
            for provider in dict.fromkeys(providers)
            if providers.count(provider) > 1
        )
        if duplicate_providers:
            raise ValueError(
                "duplicate provider records: " + ", ".join(duplicate_providers)
            )

        source_modules = tuple(record.module for record in self.source_modules)
        duplicate_source_modules = tuple(
            module
            for module in dict.fromkeys(source_modules)
            if source_modules.count(module) > 1
        )
        if duplicate_source_modules:
            raise ValueError(
                "duplicate source module records: "
                + ", ".join(duplicate_source_modules)
            )

        named_class_keys = tuple(
            (record.role, record.provider) for record in self.named_classes
        )
        duplicate_named_classes = tuple(
            key
            for key in dict.fromkeys(named_class_keys)
            if named_class_keys.count(key) > 1
        )
        if duplicate_named_classes:
            duplicate_descriptions = tuple(
                f"{role}:{provider}" for role, provider in duplicate_named_classes
            )
            raise ValueError(
                "duplicate named class records: "
                + ", ".join(duplicate_descriptions)
            )

        concrete_classes = tuple(
            record.concrete_class for record in self.concrete_parents
        )
        duplicate_concrete_classes = tuple(
            concrete_class
            for concrete_class in dict.fromkeys(concrete_classes)
            if concrete_classes.count(concrete_class) > 1
        )
        if duplicate_concrete_classes:
            raise ValueError(
                "duplicate concrete parent records: "
                + ", ".join(duplicate_concrete_classes)
            )

        declared_providers = frozenset(providers)
        referenced_providers = frozenset(
            provider
            for projection in self.projections
            for provider in (*projection.provider_bases, *projection.provider_mro)
        ) | frozenset(
            provider
            for concrete_parent in self.concrete_parents
            for provider in (
                *concrete_parent.parent_provider_mro,
                *concrete_parent.element_provider_mro,
            )
        )
        unresolved_references = tuple(
            sorted(referenced_providers - declared_providers)
        )
        if unresolved_references:
            raise ValueError(
                "unresolved provider reference: "
                + ", ".join(unresolved_references)
            )
        return self

    @model_validator(mode="after")
    def _validate_named_class_projection_consistency(self) -> Self:
        projection_by_provider = self.projection_by_provider
        for named_class in self.named_classes:
            projection = projection_by_provider.get(named_class.provider)
            if projection is None:
                raise PydanticCustomError(
                    "named_class_projection_mismatch",
                    "named class trace has no matching provider projection",
                    {"provider": named_class.provider, "field": "provider"},
                )
            for field_name, traced_value, projected_value in (
                ("role", named_class.role, projection.role),
                ("runtime_class", named_class.runtime_class, projection.runtime_class),
                ("runtime_bases", named_class.runtime_bases, projection.runtime_bases),
                ("runtime_mro", named_class.runtime_mro, projection.runtime_mro),
            ):
                if traced_value != projected_value:
                    raise PydanticCustomError(
                        "named_class_projection_mismatch",
                        "named class trace disagrees with provider projection",
                        {"provider": named_class.provider, "field": field_name},
                    )
        return self

    @model_validator(mode="after")
    def _validate_source_module_coverage(self) -> Self:
        source_modules = frozenset(record.module for record in self.source_modules)
        if not source_modules:
            return self

        missing_symbols = tuple(
            fullname
            for fullname in _semantic_fullnames(self)
            if not _fullname_has_source_module_coverage(fullname, source_modules)
        )
        if missing_symbols:
            raise PydanticCustomError(
                "source_module_coverage",
                "source-backed symbols lack source module coverage",
                {"symbols": ", ".join(missing_symbols)},
            )
        return self

    @model_validator(mode="after")
    def _validate_mypy_interval(self) -> Self:
        mypy_min = Version(self.mypy_min_version)
        mypy_max = Version(self.mypy_max_version)
        if mypy_min > mypy_max:
            raise ValueError(
                f"incompatible mypy version interval: {self.mypy_min_version!r} > "
                f"{self.mypy_max_version!r}"
            )
        mypy_current = Version(MYPY_VERSION.split("+", maxsplit=1)[0])
        if not (mypy_min <= mypy_current <= mypy_max):
            raise ValueError(
                f"incompatible mypy version for this manifest: "
                f"{self.mypy_min_version!r} <= {mypy_current!r} <= "
                f"{self.mypy_max_version!r} required"
            )
        return self

    @property
    def projection_by_provider(self) -> dict[str, ProviderProjection]:
        return {projection.provider: projection for projection in self.projections}

    @property
    def source_module_by_module(self) -> dict[str, SourceModuleRecord]:
        return {record.module: record for record in self.source_modules}

    @property
    def concrete_parent_by_class(self) -> dict[str, ConcreteParentRecord]:
        return {record.concrete_class: record for record in self.concrete_parents}

    @property
    def source_module_digest(self) -> str:
        source_modules = tuple(
            (record.module, record.path, record.sha256, record.mtime_ns)
            for record in sorted(
                self.source_modules,
                key=lambda record: record.module,
            )
        )
        digest_payload = json.dumps(
            source_modules,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(digest_payload.encode()).hexdigest()

    @property
    def semantic_projection_digest(self) -> str:
        projections = tuple(
            (
                projection.provider,
                projection.role,
                projection.runtime_class,
                projection.runtime_bases,
                projection.runtime_mro,
                projection.provider_bases,
                projection.provider_mro,
                projection.unprojected_runtime_mro,
            )
            for projection in sorted(
                self.projections,
                key=lambda projection: projection.provider,
            )
        )
        digest_payload = json.dumps(
            {
                "concrete_parents": tuple(
                    (
                        record.concrete_class,
                        record.runtime_class,
                        record.runtime_mro,
                        record.category_class,
                        record.parent_provider_mro,
                        record.element_runtime_class,
                        record.element_provider_mro,
                    )
                    for record in sorted(
                        self.concrete_parents,
                        key=lambda record: record.concrete_class,
                    )
                ),
                "named_classes": tuple(
                    (
                        record.category,
                        record.provider,
                        record.role,
                        record.trace_source,
                        record.runtime_class,
                        record.runtime_bases,
                        record.runtime_mro,
                        record.runtime_attr,
                        record.provider_attr,
                    )
                    for record in sorted(
                        self.named_classes,
                        key=lambda record: (record.role, record.provider),
                    )
                ),
                "projections": projections,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(digest_payload.encode()).hexdigest()


def _semantic_fullnames(manifest: ProjectionManifest) -> tuple[str, ...]:
    fullnames: list[str] = []
    for projection in manifest.projections:
        fullnames.extend(
            (
                projection.provider,
                projection.runtime_class,
                *projection.runtime_bases,
                *projection.runtime_mro,
                *projection.provider_bases,
                *projection.provider_mro,
                *projection.unprojected_runtime_mro,
            )
        )
    for named_class in manifest.named_classes:
        fullnames.extend(
            (
                named_class.category,
                named_class.provider,
                named_class.runtime_class,
                *named_class.runtime_bases,
                *named_class.runtime_mro,
            )
        )
    for concrete_parent in manifest.concrete_parents:
        fullnames.extend(
            (
                concrete_parent.concrete_class,
                concrete_parent.runtime_class,
                *concrete_parent.runtime_mro,
                concrete_parent.category_class,
                *concrete_parent.parent_provider_mro,
                *concrete_parent.element_provider_mro,
            )
        )
        if concrete_parent.element_runtime_class is not None:
            fullnames.append(concrete_parent.element_runtime_class)
    return tuple(dict.fromkeys(fullnames))


def _fullname_has_source_module_coverage(
    fullname: str,
    source_modules: frozenset[str],
) -> bool:
    if any(_fullname_belongs_to_module(fullname, module) for module in INTRINSIC_MODULES):
        return True
    return any(_fullname_belongs_to_module(fullname, module) for module in source_modules)


def _fullname_belongs_to_module(fullname: str, module: str) -> bool:
    return fullname == module or fullname.startswith(f"{module}.")


def load_manifest(path: Path) -> ProjectionManifest:
    return ProjectionManifest.model_validate_json(path.read_text())


def write_manifest(path: Path, manifest: ProjectionManifest) -> None:
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True)
        + "\n"
    )


__all__ = [
    "ConcreteParentRecord",
    "NamedClassRecord",
    "SourceModuleRecord",
    "ProjectionManifest",
    "load_manifest",
    "write_manifest",
]
