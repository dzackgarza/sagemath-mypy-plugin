from __future__ import annotations

from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    StrictStr,
    ValidationInfo,
    field_validator,
    model_validator,
)

ProviderRole = Literal[
    "parent",
    "element",
    "subcategory",
    "morphism",
    "homset_parent",
    "homset_element",
]
ProviderMethodReturnType = Literal["Self", "object"]
ExternalRuntimeClassStaticSignatureSource = Literal[
    "python_source",
    "stub",
    "untyped_external",
]
ROLE_PROJECTION_ALIASES: frozenset[frozenset[ProviderRole]] = frozenset(
    (
        frozenset(("parent", "homset_parent")),
        frozenset(("element", "homset_element")),
    )
)


def roles_share_projection(left: ProviderRole, right: ProviderRole) -> bool:
    if left == right:
        return True
    return frozenset((left, right)) in ROLE_PROJECTION_ALIASES


def validate_dotted_name(
    value: str,
    *,
    require_dot: bool,
) -> str:
    parts = value.split(".")
    if not value or any(not part.isidentifier() for part in parts):
        raise ValueError(f"expected dotted Python name, got {value!r}")
    if require_dot and len(parts) < 2:
        raise ValueError(f"expected dotted Python fullname, got {value!r}")
    return value


def validate_dotted_fullname(value: str) -> str:
    return validate_dotted_name(value, require_dot=True)


def validate_module_name(value: str) -> str:
    return validate_dotted_name(value, require_dot=False)


def validate_dotted_fullnames(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(validate_dotted_fullname(value) for value in values)


class ProviderProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: StrictStr
    role: ProviderRole
    runtime_class: StrictStr
    runtime_bases: tuple[StrictStr, ...]
    runtime_mro: tuple[StrictStr, ...]
    provider_bases: tuple[StrictStr, ...]
    provider_mro: tuple[StrictStr, ...]
    unprojected_runtime_mro: tuple[StrictStr, ...] = ()

    @field_validator("provider", "runtime_class")
    @classmethod
    def _validate_fullname(cls, value: str) -> str:
        return validate_dotted_fullname(value)

    @field_validator(
        "runtime_bases",
        "runtime_mro",
        "provider_bases",
        "provider_mro",
        "unprojected_runtime_mro",
    )
    @classmethod
    def _validate_fullname_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return validate_dotted_fullnames(value)

    @field_validator("provider_bases", "provider_mro")
    @classmethod
    def _validate_unique_fullname_tuple(
        cls,
        value: tuple[str, ...],
        info: ValidationInfo,
    ) -> tuple[str, ...]:
        duplicates = tuple(
            fullname
            for fullname in dict.fromkeys(value)
            if value.count(fullname) > 1
        )
        if duplicates:
            raise ValueError(
                f"duplicate {info.field_name} entries: " + ", ".join(duplicates)
            )
        return value


class ConcreteParentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    concrete_class: StrictStr
    runtime_class: StrictStr
    runtime_mro: tuple[StrictStr, ...]
    category_class: StrictStr
    parent_provider_mro: tuple[StrictStr, ...]
    element_runtime_class: StrictStr | None = None
    element_runtime_mro: tuple[StrictStr, ...] = ()
    element_provider_mro: tuple[StrictStr, ...] = ()

    @field_validator(
        "concrete_class",
        "runtime_class",
        "category_class",
        "element_runtime_class",
    )
    @classmethod
    def _validate_fullname_or_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_dotted_fullname(value)

    @field_validator(
        "runtime_mro",
        "parent_provider_mro",
        "element_runtime_mro",
        "element_provider_mro",
    )
    @classmethod
    def _validate_fullname_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return validate_dotted_fullnames(value)


class ProviderMethodRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: StrictStr
    name: StrictStr
    return_type: ProviderMethodReturnType

    @field_validator("provider")
    @classmethod
    def _validate_provider_fullname(cls, value: str) -> str:
        return validate_dotted_fullname(value)

    @model_validator(mode="after")
    def _validate_method_signature(self) -> Self:
        if not self.name.isidentifier():
            raise ValueError(f"method name must be a Python identifier: {self.name!r}")
        return self


class ExternalRuntimeClassRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime_class: StrictStr
    module: StrictStr
    static_signature_source: ExternalRuntimeClassStaticSignatureSource
    source_module: StrictStr | None = None

    @field_validator("runtime_class")
    @classmethod
    def _validate_runtime_class_fullname(cls, value: str) -> str:
        return validate_dotted_fullname(value)

    @field_validator("module", "source_module")
    @classmethod
    def _validate_module_or_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_module_name(value)

    @model_validator(mode="after")
    def _validate_static_signature_source(self) -> Self:
        if self.static_signature_source == "untyped_external":
            if self.source_module is not None:
                raise ValueError(
                    "untyped external runtime classes must not claim a source module"
                )
            return self

        if self.source_module is None:
            raise ValueError(
                f"{self.static_signature_source} runtime classes require "
                "source_module"
            )
        return self


__all__ = [
    "ConcreteParentRecord",
    "ExternalRuntimeClassRecord",
    "ExternalRuntimeClassStaticSignatureSource",
    "ProviderMethodReturnType",
    "ProviderMethodRecord",
    "ProviderProjection",
    "ProviderRole",
    "roles_share_projection",
]
