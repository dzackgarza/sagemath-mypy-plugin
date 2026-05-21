from __future__ import annotations

import json
from hashlib import sha256
import re

from pathlib import Path
from typing import Literal, Self

from mypy.version import __version__ as MYPY_VERSION
from packaging.version import Version
from pydantic import (
    BaseModel,
    ConfigDict,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from sage_mypy_category_plugin.projection import (
    ConcreteParentRecord,
    ExternalRuntimeClassRecord,
    ProviderMethodRecord,
    ProviderProjection,
    ProviderRole,
    roles_share_projection,
    validate_dotted_fullname,
    validate_dotted_fullnames,
    validate_module_name,
)

CURRENT_PLUGIN_SCHEMA_VERSION: Literal["1"] = "1"
SHA256_HEX_PATTERN = re.compile(r"[0-9a-f]{64}")
GIT_REVISION_PATTERN = re.compile(r"[0-9a-f]{40}")
INTRINSIC_MODULES = frozenset(("builtins",))


class SourceModuleRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    module: StrictStr
    path: StrictStr
    sha256: StrictStr
    mtime_ns: StrictInt

    @field_validator("module")
    @classmethod
    def _validate_module_name(cls, value: str) -> str:
        return validate_module_name(value)

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

    @field_validator("category", "provider", "runtime_class")
    @classmethod
    def _validate_fullname(cls, value: str) -> str:
        return validate_dotted_fullname(value)

    @field_validator("runtime_bases", "runtime_mro")
    @classmethod
    def _validate_fullname_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return validate_dotted_fullnames(value)


class UnsupportedProviderRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: StrictStr
    role: ProviderRole
    reason: Literal["ambiguous_runtime_mro"]
    runtime_classes: tuple[StrictStr, ...]
    runtime_mros: tuple[tuple[StrictStr, ...], ...]

    @field_validator("provider")
    @classmethod
    def _validate_fullname(cls, value: str) -> str:
        return validate_dotted_fullname(value)

    @field_validator("runtime_classes")
    @classmethod
    def _validate_runtime_classes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return validate_dotted_fullnames(value)

    @field_validator("runtime_mros")
    @classmethod
    def _validate_runtime_mros(
        cls,
        value: tuple[tuple[str, ...], ...],
    ) -> tuple[tuple[str, ...], ...]:
        return tuple(validate_dotted_fullnames(runtime_mro) for runtime_mro in value)

    @model_validator(mode="after")
    def _validate_runtime_mro_evidence(self) -> Self:
        if len(self.runtime_classes) < 1:
            raise PydanticCustomError(
                "unsupported_provider_graph_mismatch",
                "unsupported providers require at least one runtime class",
                {"provider": self.provider, "field": "runtime_classes"},
            )
        if len(self.runtime_classes) != len(self.runtime_mros):
            raise PydanticCustomError(
                "unsupported_provider_graph_mismatch",
                "unsupported provider runtime class and MRO counts must agree",
                {"provider": self.provider, "field": "runtime_mros"},
            )
        duplicate_runtime_classes = tuple(
            runtime_class
            for runtime_class in dict.fromkeys(self.runtime_classes)
            if self.runtime_classes.count(runtime_class) > 1
        )
        if duplicate_runtime_classes:
            raise PydanticCustomError(
                "unsupported_provider_graph_mismatch",
                "duplicate unsupported provider runtime classes",
                {"provider": self.provider, "field": "runtime_classes"},
            )
        for runtime_class, runtime_mro in zip(
            self.runtime_classes,
            self.runtime_mros,
            strict=True,
        ):
            if not runtime_mro or runtime_mro[0] != runtime_class:
                raise PydanticCustomError(
                    "unsupported_provider_graph_mismatch",
                    "unsupported provider runtime MRO must start with its "
                    "runtime class",
                    {"provider": self.provider, "field": "runtime_mros"},
                )
        return self


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
    unsupported_providers: tuple[UnsupportedProviderRecord, ...] = ()
    projections: tuple[ProviderProjection, ...]
    provider_methods: tuple[ProviderMethodRecord, ...] = ()
    source_modules: tuple[SourceModuleRecord, ...] = ()
    concrete_parents: tuple[ConcreteParentRecord, ...] = ()
    external_runtime_classes: tuple[ExternalRuntimeClassRecord, ...] = ()

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

        external_runtime_classes = tuple(
            record.runtime_class for record in self.external_runtime_classes
        )
        duplicate_external_runtime_classes = tuple(
            runtime_class
            for runtime_class in dict.fromkeys(external_runtime_classes)
            if external_runtime_classes.count(runtime_class) > 1
        )
        if duplicate_external_runtime_classes:
            raise ValueError(
                "duplicate external runtime class records: "
                + ", ".join(duplicate_external_runtime_classes)
            )

        unsupported_provider_keys = tuple(
            (record.role, record.provider) for record in self.unsupported_providers
        )
        duplicate_unsupported_providers = tuple(
            key
            for key in dict.fromkeys(unsupported_provider_keys)
            if unsupported_provider_keys.count(key) > 1
        )
        if duplicate_unsupported_providers:
            duplicate_descriptions = tuple(
                f"{role}:{provider}"
                for role, provider in duplicate_unsupported_providers
            )
            raise ValueError(
                "duplicate unsupported provider records: "
                + ", ".join(duplicate_descriptions)
            )
        supported_and_unsupported_providers = tuple(
            (unsupported_provider.role, unsupported_provider.provider)
            for unsupported_provider in self.unsupported_providers
            if any(
                projection.provider == unsupported_provider.provider
                and roles_share_projection(projection.role, unsupported_provider.role)
                for projection in self.projections
            )
        )
        if supported_and_unsupported_providers:
            role, provider = supported_and_unsupported_providers[0]
            raise PydanticCustomError(
                "unsupported_provider_projection_overlap",
                "provider cannot be both supported and unsupported",
                {"provider": provider, "role": role},
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

        provider_method_keys = tuple(
            (record.provider, record.name) for record in self.provider_methods
        )
        duplicate_provider_methods = tuple(
            key
            for key in dict.fromkeys(provider_method_keys)
            if provider_method_keys.count(key) > 1
        )
        if duplicate_provider_methods:
            duplicate_descriptions = tuple(
                f"{provider}:{name}" for provider, name in duplicate_provider_methods
            )
            raise ValueError(
                "duplicate provider method records: "
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

        for concrete_parent in self.concrete_parents:
            if (
                not concrete_parent.runtime_mro
                or concrete_parent.runtime_mro[0] != concrete_parent.runtime_class
            ):
                raise PydanticCustomError(
                    "concrete_parent_graph_mismatch",
                    "concrete parent runtime MRO must start with its runtime class",
                    {
                        "concrete_class": concrete_parent.concrete_class,
                        "field": "runtime_mro",
                    },
                )
            if not concrete_parent.parent_provider_mro:
                raise PydanticCustomError(
                    "concrete_parent_graph_mismatch",
                    "concrete parent record must include a parent provider MRO",
                    {
                        "concrete_class": concrete_parent.concrete_class,
                        "field": "parent_provider_mro",
                    },
                )
            if (
                concrete_parent.element_runtime_class is None
                and concrete_parent.element_provider_mro
            ):
                raise PydanticCustomError(
                    "concrete_parent_graph_mismatch",
                    "element provider MRO requires an element runtime class",
                    {
                        "concrete_class": concrete_parent.concrete_class,
                        "field": "element_runtime_class",
                    },
                )
            if (
                concrete_parent.element_runtime_class is None
                and concrete_parent.element_runtime_mro
            ):
                raise PydanticCustomError(
                    "concrete_parent_graph_mismatch",
                    "element runtime MRO requires an element runtime class",
                    {
                        "concrete_class": concrete_parent.concrete_class,
                        "field": "element_runtime_class",
                    },
                )
            if (
                concrete_parent.element_runtime_class is not None
                and not concrete_parent.element_provider_mro
            ):
                raise PydanticCustomError(
                    "concrete_parent_graph_mismatch",
                    "element runtime class requires an element provider MRO",
                    {
                        "concrete_class": concrete_parent.concrete_class,
                        "field": "element_provider_mro",
                    },
                )
            if (
                concrete_parent.element_runtime_class is not None
                and not concrete_parent.element_runtime_mro
            ):
                raise PydanticCustomError(
                    "concrete_parent_graph_mismatch",
                    "element runtime class requires an element runtime MRO",
                    {
                        "concrete_class": concrete_parent.concrete_class,
                        "field": "element_runtime_mro",
                    },
                )
            if (
                concrete_parent.element_runtime_mro
                and concrete_parent.element_runtime_mro[0]
                != concrete_parent.element_runtime_class
            ):
                raise PydanticCustomError(
                    "concrete_parent_graph_mismatch",
                    "concrete parent element runtime MRO must start with its "
                    "runtime class",
                    {
                        "concrete_class": concrete_parent.concrete_class,
                        "field": "element_runtime_mro",
                    },
                )

        for projection in self.projections:
            if (
                not projection.provider_mro
                or projection.provider_mro[0] != projection.provider
            ):
                raise PydanticCustomError(
                    "projection_graph_mismatch",
                    "provider projection MRO must start with its provider",
                    {"provider": projection.provider, "field": "provider_mro"},
                )
            if (
                not projection.runtime_mro
                or projection.runtime_mro[0] != projection.runtime_class
            ):
                raise PydanticCustomError(
                    "projection_graph_mismatch",
                    "runtime MRO must start with its runtime class",
                    {"provider": projection.provider, "field": "runtime_mro"},
                )

            missing_provider_bases = tuple(
                provider_base
                for provider_base in projection.provider_bases
                if provider_base not in projection.provider_mro[1:]
            )
            if missing_provider_bases:
                raise PydanticCustomError(
                    "projection_graph_mismatch",
                    "provider bases must appear in provider MRO",
                    {"provider": projection.provider, "field": "provider_bases"},
                )

            missing_runtime_bases = tuple(
                runtime_base
                for runtime_base in projection.runtime_bases
                if runtime_base not in projection.runtime_mro[1:]
            )
            if missing_runtime_bases:
                raise PydanticCustomError(
                    "projection_graph_mismatch",
                    "runtime bases must appear in runtime MRO",
                    {"provider": projection.provider, "field": "runtime_bases"},
                )

        declared_external_runtime_classes = frozenset(external_runtime_classes)
        unclassified_external_runtime_classes = tuple(
            runtime_class
            for projection in self.projections
            for runtime_class in projection.unprojected_runtime_mro
            if runtime_class not in declared_external_runtime_classes
        )
        if unclassified_external_runtime_classes:
            raise PydanticCustomError(
                "external_runtime_class_missing",
                "unprojected runtime classes require external boundary metadata",
                {"runtime_class": unclassified_external_runtime_classes[0]},
            )

        declared_source_modules = frozenset(source_modules)
        missing_external_source_modules = tuple(
            record.source_module
            for record in self.external_runtime_classes
            if record.source_module is not None
            and record.source_module not in declared_source_modules
        )
        if missing_external_source_modules:
            raise PydanticCustomError(
                "external_runtime_class_source_module_missing",
                "external runtime class source modules must be declared",
                {"source_module": missing_external_source_modules[0]},
            )

        declared_providers = frozenset(providers)
        declared_reference_providers = declared_providers | frozenset(
            record.provider for record in self.unsupported_providers
        )
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
        referenced_method_providers = frozenset(
            record.provider for record in self.provider_methods
        )
        unresolved_references = tuple(
            sorted(
                (referenced_providers | referenced_method_providers)
                - declared_reference_providers
            )
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
            if not roles_share_projection(named_class.role, projection.role):
                raise PydanticCustomError(
                    "named_class_projection_mismatch",
                    "named class trace disagrees with provider projection",
                    {"provider": named_class.provider, "field": "role"},
                )
            for field_name, traced_value, projected_value in (
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
    def external_runtime_class_by_fullname(
        self,
    ) -> dict[str, ExternalRuntimeClassRecord]:
        return {
            record.runtime_class: record for record in self.external_runtime_classes
        }

    @property
    def unsupported_provider_by_role_and_provider(
        self,
    ) -> dict[tuple[ProviderRole, str], UnsupportedProviderRecord]:
        return {
            (record.role, record.provider): record
            for record in self.unsupported_providers
        }

    @property
    def unsupported_provider_by_provider(self) -> dict[str, UnsupportedProviderRecord]:
        providers = tuple(record.provider for record in self.unsupported_providers)
        duplicate_providers = tuple(
            provider
            for provider in dict.fromkeys(providers)
            if providers.count(provider) > 1
        )
        if duplicate_providers:
            raise ValueError(
                "unsupported provider lookup by provider is ambiguous for: "
                + ", ".join(duplicate_providers)
            )
        return {record.provider: record for record in self.unsupported_providers}

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
                        record.element_runtime_mro,
                        record.element_provider_mro,
                    )
                    for record in sorted(
                        self.concrete_parents,
                        key=lambda record: record.concrete_class,
                    )
                ),
                "provider_methods": tuple(
                    (
                        record.provider,
                        record.name,
                        record.return_type,
                    )
                    for record in sorted(
                        self.provider_methods,
                        key=lambda record: (record.provider, record.name),
                    )
                ),
                "external_runtime_classes": tuple(
                    (
                        record.runtime_class,
                        record.module,
                        record.static_signature_source,
                        record.source_module,
                    )
                    for record in sorted(
                        self.external_runtime_classes,
                        key=lambda record: record.runtime_class,
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
                "unsupported_providers": tuple(
                    (
                        record.provider,
                        record.role,
                        record.reason,
                        record.runtime_classes,
                        record.runtime_mros,
                    )
                    for record in sorted(
                        self.unsupported_providers,
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
    for unsupported_provider in manifest.unsupported_providers:
        fullnames.extend(
            (
                unsupported_provider.provider,
                *unsupported_provider.runtime_classes,
                *(
                    runtime_class
                    for runtime_mro in unsupported_provider.runtime_mros
                    for runtime_class in runtime_mro
                ),
            )
        )
    for provider_method in manifest.provider_methods:
        fullnames.append(provider_method.provider)
    for external_runtime_class in manifest.external_runtime_classes:
        if external_runtime_class.source_module is not None:
            fullnames.append(external_runtime_class.runtime_class)
    for concrete_parent in manifest.concrete_parents:
        fullnames.extend(
            (
                concrete_parent.concrete_class,
                concrete_parent.runtime_class,
                *concrete_parent.runtime_mro,
                concrete_parent.category_class,
                *concrete_parent.parent_provider_mro,
                *concrete_parent.element_runtime_mro,
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
    "ExternalRuntimeClassRecord",
    "NamedClassRecord",
    "ProviderMethodRecord",
    "SourceModuleRecord",
    "ProjectionManifest",
    "UnsupportedProviderRecord",
    "load_manifest",
    "write_manifest",
]
