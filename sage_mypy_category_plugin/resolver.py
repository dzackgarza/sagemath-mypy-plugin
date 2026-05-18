from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Iterable
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from sys import version_info
from typing import Sequence, cast, get_args

from mypy.version import __version__ as MYPY_VERSION

from sage_mypy_category_plugin.manifest import (
    NamedClassRecord,
    ProjectionManifest,
    SourceModuleRecord,
    write_manifest,
)
from sage_mypy_category_plugin.imports import importable_module_name_or_none
from sage_mypy_category_plugin.oracle import (
    concrete_parent_records_for_factories,
    named_class_traces,
    provider_method_records_for_projections,
    provider_projections_for_categories,
)
from sage_mypy_category_plugin.projection import (
    ConcreteParentRecord,
    ProviderProjection,
    ProviderRole,
)


def resolve_projection_manifest(
    *,
    category_fullnames: Sequence[str],
    roles: Sequence[ProviderRole],
    concrete_parent_fullnames: Sequence[str] = (),
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
    concrete_parents = tuple(
        concrete_parent_records_for_factories(concrete_parent_fullnames).values()
    )

    return ProjectionManifest(
        schema_version=1,
        generated_by=generated_by,
        sage_version=sage_version,
        sage_git_revision=sage_git_revision,
        python_version=f"{version_info.major}.{version_info.minor}.{version_info.micro}",
        mypy_min_version=mypy_min_version,
        mypy_max_version=mypy_max_version,
        named_classes=_named_class_records(),
        projections=tuple(projections.values()),
        provider_methods=provider_method_records_for_projections(projections.values()),
        concrete_parents=concrete_parents,
        source_modules=_source_module_records(
            category_fullnames,
            projections=projections.values(),
            concrete_parents=concrete_parents,
        ),
    )


def _named_class_records() -> tuple[NamedClassRecord, ...]:
    return tuple(
        NamedClassRecord(
            category=trace.category,
            provider=trace.provider,
            role=trace.role,
            trace_source=trace.trace_source,
            runtime_class=trace.runtime_class,
            runtime_bases=trace.runtime_bases,
            runtime_mro=trace.runtime_mro,
            runtime_attr=trace.runtime_attr,
            provider_attr=trace.provider_attr,
        )
        for trace in named_class_traces()
    )


def write_projection_manifest(
    *,
    output: Path,
    category_fullnames: Sequence[str],
    roles: Sequence[ProviderRole],
    concrete_parent_fullnames: Sequence[str] = (),
    generated_by: str = "sage-mypy-category-plugin",
    sage_version: str | None = None,
    sage_git_revision: str | None = None,
    mypy_min_version: str = MYPY_VERSION,
    mypy_max_version: str = MYPY_VERSION,
) -> ProjectionManifest:
    manifest = resolve_projection_manifest(
        category_fullnames=category_fullnames,
        roles=roles,
        concrete_parent_fullnames=concrete_parent_fullnames,
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
        "--concrete-parent",
        action="append",
        default=[],
        help=(
            "Fully-qualified concrete Sage parent class to instantiate and record. "
            "Pass multiple times for multiple concrete parents."
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
    *,
    projections: Iterable[ProviderProjection] = (),
    concrete_parents: Iterable[ConcreteParentRecord] = (),
) -> tuple[SourceModuleRecord, ...]:
    module_names = tuple(
        dict.fromkeys(
            (
                *(
                    _category_module_name(fullname)
                    for fullname in category_fullnames
                ),
                *_projection_module_names(projections),
                *_concrete_parent_module_names(concrete_parents),
            )
        )
    )
    return tuple(
        record
        for module_name in module_names
        if (record := _source_module_record_or_none(module_name)) is not None
    )


def _projection_module_names(
    projections: Iterable[ProviderProjection],
) -> tuple[str, ...]:
    module_names: list[str] = []
    for projection in projections:
        for fullname in (
            projection.provider,
            projection.runtime_class,
            *projection.runtime_bases,
            *projection.runtime_mro,
            *projection.provider_bases,
            *projection.provider_mro,
            *projection.unprojected_runtime_mro,
        ):
            module_name = _importable_module_name_or_none(fullname)
            if module_name is not None:
                module_names.append(module_name)
    return tuple(dict.fromkeys(module_names))


def _concrete_parent_module_names(
    concrete_parents: Iterable[ConcreteParentRecord],
) -> tuple[str, ...]:
    module_names: list[str] = []
    for concrete_parent in concrete_parents:
        for fullname in (
            concrete_parent.concrete_class,
            concrete_parent.runtime_class,
            *concrete_parent.runtime_mro,
            concrete_parent.category_class,
            *concrete_parent.parent_provider_mro,
            *concrete_parent.element_provider_mro,
        ):
            module_name = _importable_module_name_or_none(fullname)
            if module_name is not None:
                module_names.append(module_name)
        if concrete_parent.element_runtime_class is not None:
            module_name = _importable_module_name_or_none(
                concrete_parent.element_runtime_class
            )
            if module_name is not None:
                module_names.append(module_name)
    return tuple(dict.fromkeys(module_names))


def _importable_module_name_or_none(fullname: str) -> str | None:
    return importable_module_name_or_none(fullname)


def _category_module_name(category_fullname: str) -> str:
    module_name = _importable_module_name_or_none(category_fullname)
    if module_name is None:
        raise ValueError(f"Expected importable category name: {category_fullname!r}")
    return module_name


def _source_module_record_or_none(module_name: str) -> SourceModuleRecord | None:
    module = import_module(module_name)
    module_file = getattr(module, "__file__", None)
    if module_file is None:
        return None
    path = Path(module_file)
    source_stat = path.stat()
    source_bytes = path.read_bytes()
    return SourceModuleRecord(
        module=module_name,
        path=str(_relative_to_cwd(path)),
        sha256=sha256(source_bytes).hexdigest(),
        mtime_ns=source_stat.st_mtime_ns,
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
        concrete_parent_fullnames=list(args.concrete_parent),
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
