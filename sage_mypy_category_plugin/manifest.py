from __future__ import annotations

import json

from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, StrictStr, model_validator

from sage_mypy_category_plugin.projection import ProviderProjection


class ProjectionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    generated_by: StrictStr
    sage_version: StrictStr
    python_version: StrictStr
    projections: tuple[ProviderProjection, ...]

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

        declared_providers = frozenset(providers)
        referenced_providers = frozenset(
            provider
            for projection in self.projections
            for provider in (*projection.provider_bases, *projection.provider_mro)
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

    @property
    def projection_by_provider(self) -> dict[str, ProviderProjection]:
        return {projection.provider: projection for projection in self.projections}


def load_manifest(path: Path) -> ProjectionManifest:
    return ProjectionManifest.model_validate_json(path.read_text())


def write_manifest(path: Path, manifest: ProjectionManifest) -> None:
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True)
        + "\n"
    )


__all__ = [
    "ProjectionManifest",
    "load_manifest",
    "write_manifest",
]
