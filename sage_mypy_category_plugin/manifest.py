from __future__ import annotations

import json

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictStr

from sage_mypy_category_plugin.projection import ProviderProjection


class ProjectionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    generated_by: StrictStr
    sage_version: StrictStr
    python_version: StrictStr
    projections: tuple[ProviderProjection, ...]

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
