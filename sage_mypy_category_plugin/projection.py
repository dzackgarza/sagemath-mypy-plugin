from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictStr

ProviderRole = Literal["parent", "element", "subcategory", "morphism"]


class ProviderProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: StrictStr
    role: ProviderRole
    runtime_class: StrictStr
    runtime_bases: tuple[StrictStr, ...]
    runtime_mro: tuple[StrictStr, ...]
    provider_bases: tuple[StrictStr, ...]
    provider_mro: tuple[StrictStr, ...]


__all__ = [
    "ProviderProjection",
    "ProviderRole",
]
