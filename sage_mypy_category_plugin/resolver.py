from __future__ import annotations

from argparse import ArgumentParser
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from typing import Sequence, cast, get_args
from sys import version_info

from mypy.version import __version__ as MYPY_VERSION

from sage_mypy_category_plugin.manifest import (
    ProjectionManifest,
    SourceModuleRecord,
    write_manifest,
)
from sage_mypy_category_plugin.oracle import provider_projections_for_categories
from sage_mypy_category_plugin.projection import ProviderRole


def resolve_projection_manifest(
    *,
    category_fullnames: Sequence[str],
    roles: Sequence[ProviderRole],
    generated_by: str = "sage-mypy-category-plugin",
    sage_version: str | None = None,
    sage_git_revision: str | None = None,
    mypy_min_version: str = MYPY_VERSION,
    mypy_max_version: str = MYPY_VERSION,
) -> ProjectionManifest:
    if sage_version is None:
        from sage.version import version as _sage_version  # type: ignore[import-untyped]

        sage_version = str(_sage_version)

    projections = provider_projections_for_categories(
        category_fullnames,
        roles=roles,
    )

    return ProjectionManifest(
        schema_version=1,
        generated_by=generated_by,
        sage_version=sage_version,
        sage_git_revision=sage_git_revision,
        python_version=f"{version_info.major}.{version_info.minor}.{version_info.micro}",
        mypy_min_version=mypy_min_version,
        mypy_max_version=mypy_max_version,
        projections=tuple(projections.values()),
        source_modules=_source_module_records(category_fullnames),
    )


def write_projection_manifest(
    *,
    output: Path,
    category_fullnames: Sequence[str],
    roles: Sequence[ProviderRole],
    generated_by: str = "sage-mypy-category-plugin",
    sage_version: str | None = None,
    sage_git_revision: str | None = None,
    mypy_min_version: str = MYPY_VERSION,
    mypy_max_version: str = MYPY_VERSION,
) -> ProjectionManifest:
    manifest = resolve_projection_manifest(
        category_fullnames=category_fullnames,
        roles=roles,
        generated_by=generated_by,
        sage_version=sage_version,
        sage_git_revision=sage_git_revision,
        mypy_min_version=mypy_min_version,
        mypy_max_version=mypy_max_version,
    )
    write_manifest(output, manifest)
    return manifest


def _resolver_argument_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="sage_mypy_category_plugin.resolver",
        description=(
            "Resolve Sage category method-provider inheritance and write a projection "
            "manifest."
        ),
    )
    parser.add_argument(
        "category_fullnames",
        nargs="+",
        help="Fully-qualified category factory classes to resolve.",
    )
    parser.add_argument(
        "--role",
        action="append",
        default=[],
        choices=get_args(ProviderRole),
        help=(
            "Provider role to resolve. Pass multiple times for multiple roles. "
            "Defaults to parent."
        ),
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write ProjectionManifest JSON.",
    )
    parser.add_argument(
        "--generated-by",
        default="sage-mypy-category-plugin",
        help="Manifest metadata field.",
    )
    parser.add_argument(
        "--sage-version",
        help="Override Sage version reported in the manifest.",
    )
    parser.add_argument(
        "--sage-git-revision",
        help="Override Sage git revision reported in the manifest.",
    )
    parser.add_argument(
        "--mypy-min-version",
        default=MYPY_VERSION,
        help="Minimum compatible mypy version (for manifest compatibility checks).",
    )
    parser.add_argument(
        "--mypy-max-version",
        default=MYPY_VERSION,
        help="Maximum compatible mypy version (for manifest compatibility checks).",
    )
    return parser


def _source_module_records(
    category_fullnames: Sequence[str],
) -> tuple[SourceModuleRecord, ...]:
    module_names = tuple(
        dict.fromkeys(_category_module_name(fullname) for fullname in category_fullnames)
    )
    return tuple(_source_module_record(module_name) for module_name in module_names)


def _category_module_name(category_fullname: str) -> str:
    module_name, separator, _ = category_fullname.rpartition(".")
    if separator != ".":
        raise ValueError(f"Expected fully-qualified category name: {category_fullname!r}")
    return module_name


def _source_module_record(module_name: str) -> SourceModuleRecord:
    module = import_module(module_name)
    module_file = getattr(module, "__file__", None)
    if module_file is None:
        raise ValueError(f"Module has no source file: {module_name}")
    path = Path(module_file)
    source_bytes = path.read_bytes()
    return SourceModuleRecord(
        module=module_name,
        path=str(_relative_to_cwd(path)),
        sha256=sha256(source_bytes).hexdigest(),
    )


def _relative_to_cwd(path: Path) -> Path:
    resolved_path = path.resolve()
    resolved_cwd = Path.cwd().resolve()
    if resolved_path.is_relative_to(resolved_cwd):
        return resolved_path.relative_to(resolved_cwd)
    return resolved_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = _resolver_argument_parser()
    args = parser.parse_args(argv)
    roles: tuple[ProviderRole, ...] = (
        ("parent",)
        if not args.role
        else tuple(cast(ProviderRole, role) for role in args.role)
    )
    write_projection_manifest(
        output=Path(args.output),
        category_fullnames=list(args.category_fullnames),
        roles=roles,
        generated_by=args.generated_by,
        sage_version=args.sage_version,
        sage_git_revision=args.sage_git_revision,
        mypy_min_version=args.mypy_min_version,
        mypy_max_version=args.mypy_max_version,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "main",
    "resolve_projection_manifest",
    "write_projection_manifest",
]
