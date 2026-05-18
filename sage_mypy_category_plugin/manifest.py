from __future__ import annotations

import json
from hashlib import sha256

from pathlib import Path
from typing import Literal, Self

from mypy.version import __version__ as MYPY_VERSION
from packaging.version import Version
from pydantic import BaseModel, ConfigDict, StrictStr, model_validator

from sage_mypy_category_plugin.projection import ProviderProjection

CURRENT_PLUGIN_SCHEMA_VERSION = "1"


class ProjectionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    generated_by: StrictStr
    plugin_schema_version: Literal["1"] = CURRENT_PLUGIN_SCHEMA_VERSION
    sage_version: StrictStr
    mypy_min_version: StrictStr = "0.0.0"
    mypy_max_version: StrictStr = "9999.9999.9999"
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
            )
            for projection in sorted(
                self.projections,
                key=lambda projection: projection.provider,
            )
        )
        digest_payload = json.dumps(
            projections,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(digest_payload.encode()).hexdigest()


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
