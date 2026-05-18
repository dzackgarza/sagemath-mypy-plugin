from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, StrictStr, model_validator

ProviderRole = Literal[
    "parent",
    "element",
    "subcategory",
    "morphism",
    "homset_parent",
    "homset_element",
]


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


class ConcreteParentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    concrete_class: StrictStr
    runtime_class: StrictStr
    runtime_mro: tuple[StrictStr, ...]
    category_class: StrictStr
    parent_provider_mro: tuple[StrictStr, ...]
    element_runtime_class: StrictStr | None = None
    element_provider_mro: tuple[StrictStr, ...] = ()


class ProviderMethodRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: StrictStr
    name: StrictStr
    return_type: Literal["Self"]

    @model_validator(mode="after")
    def _validate_method_signature(self) -> Self:
        if not self.name.isidentifier():
            raise ValueError(f"method name must be a Python identifier: {self.name!r}")
        return self


__all__ = [
    "ConcreteParentRecord",
    "ProviderMethodRecord",
    "ProviderProjection",
    "ProviderRole",
]
