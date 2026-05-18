from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, StrictStr, field_validator, model_validator

ProviderRole = Literal[
    "parent",
    "element",
    "subcategory",
    "morphism",
    "homset_parent",
    "homset_element",
]
ProviderMethodReturnType = Literal["Self", "object"]


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


class ConcreteParentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    concrete_class: StrictStr
    runtime_class: StrictStr
    runtime_mro: tuple[StrictStr, ...]
    category_class: StrictStr
    parent_provider_mro: tuple[StrictStr, ...]
    element_runtime_class: StrictStr | None = None
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


__all__ = [
    "ConcreteParentRecord",
    "ProviderMethodReturnType",
    "ProviderMethodRecord",
    "ProviderProjection",
    "ProviderRole",
]
