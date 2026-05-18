from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictStr

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


__all__ = [
    "ConcreteParentRecord",
    "ProviderProjection",
    "ProviderRole",
]
