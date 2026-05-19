from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Iterable
from hashlib import sha256
from inspect import Parameter, signature
from importlib import import_module
from pathlib import Path
from pkgutil import walk_packages
from sys import version_info
from types import ModuleType
from typing import Sequence, cast, get_args

from mypy.version import __version__ as MYPY_VERSION

from sage_mypy_category_plugin.manifest import (
    NamedClassRecord,
    ProjectionManifest,
    SourceModuleRecord,
    UnsupportedProviderRecord,
    write_manifest,
)
from sage_mypy_category_plugin.imports import importable_module_name_or_none
from sage_mypy_category_plugin.oracle import (
    concrete_parent_records_and_provider_projections_for_factories,
    named_class_traces,
    provider_method_records_for_projections,
    provider_projections_for_categories,
    unsupported_provider_traces,
)
from sage_mypy_category_plugin.projection import (
    ConcreteParentRecord,
    ExternalRuntimeClassRecord,
    ExternalRuntimeClassStaticSignatureSource,
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
    concrete_parent_records, concrete_parent_projections = (
        concrete_parent_records_and_provider_projections_for_factories(
            concrete_parent_fullnames
        )
    )
    for provider, projection in concrete_parent_projections.items():
        existing_projection = projections.get(provider)
        if existing_projection is not None:
            assert existing_projection == projection, (
                f"Conflicting projection for concrete parent provider {provider}: "
                f"{existing_projection!r} vs {projection!r}"
            )
            continue
        projections[provider] = projection
    concrete_parents = tuple(
        concrete_parent_records.values()
    )
    external_runtime_classes = _external_runtime_class_records(
        projections=projections.values(),
        concrete_parents=concrete_parents,
    )
    unsupported_providers = _unsupported_provider_records()

    return ProjectionManifest(
        schema_version=1,
        generated_by=generated_by,
        sage_version=sage_version,
        sage_git_revision=sage_git_revision,
        python_version=f"{version_info.major}.{version_info.minor}.{version_info.micro}",
        mypy_min_version=mypy_min_version,
        mypy_max_version=mypy_max_version,
        named_classes=_named_class_records(),
        unsupported_providers=unsupported_providers,
        projections=tuple(projections.values()),
        provider_methods=provider_method_records_for_projections(
            projections.values(),
            concrete_parents=concrete_parents,
        ),
        concrete_parents=concrete_parents,
        external_runtime_classes=external_runtime_classes,
        source_modules=_source_module_records(
            category_fullnames,
            projections=projections.values(),
            unsupported_providers=unsupported_providers,
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


def _unsupported_provider_records() -> tuple[UnsupportedProviderRecord, ...]:
    return tuple(
        UnsupportedProviderRecord(
            provider=trace.provider,
            role=trace.role,
            reason=trace.reason,
            runtime_classes=trace.runtime_classes,
            runtime_mros=trace.runtime_mros,
        )
        for trace in unsupported_provider_traces()
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


def discover_category_fullnames(package_names: Sequence[str]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            fullname
            for module in _import_package_modules(package_names)
            for fullname in _category_fullnames_defined_in_module(module)
        )
    )


def _import_package_modules(package_names: Sequence[str]) -> tuple[ModuleType, ...]:
    module_by_name: dict[str, ModuleType] = {}
    for package_name in package_names:
        package = import_module(package_name)
        module_by_name[package.__name__] = package
        for module_name in _package_module_names(package):
            module_by_name[module_name] = import_module(module_name)
    return tuple(module_by_name.values())


def _package_module_names(package: ModuleType) -> tuple[str, ...]:
    package_paths = getattr(package, "__path__", None)
    if package_paths is None:
        return ()

    walk_package_names = tuple(
        module_info.name
        for module_info in walk_packages(
            package_paths,
            prefix=f"{package.__name__}.",
        )
    )
    filesystem_names = _filesystem_package_module_names(
        package,
        package_paths=package_paths,
    )
    return tuple(dict.fromkeys((*walk_package_names, *filesystem_names)))


def _filesystem_package_module_names(
    package: ModuleType,
    *,
    package_paths: Iterable[str],
) -> tuple[str, ...]:
    module_names: list[str] = []
    for package_path in package_paths:
        package_root = Path(package_path)
        if not package_root.is_dir():
            continue
        for module_path in sorted(package_root.rglob("*.py")):
            if module_path.name == "__init__.py":
                continue
            module_names.append(
                ".".join(
                    (
                        package.__name__,
                        *module_path.relative_to(package_root)
                        .with_suffix("")
                        .parts,
                    )
                )
            )
    return tuple(module_names)


def _category_fullnames_defined_in_module(module: ModuleType) -> tuple[str, ...]:
    from sage.categories.category import Category  # type: ignore[import-untyped]
    from sage.categories.category_with_axiom import CategoryWithAxiom  # type: ignore[import-untyped]
    from sage.misc.abstract_method import AbstractMethod  # type: ignore[import-untyped]

    return tuple(
        f"{candidate.__module__}.{candidate.__qualname__}"
        for candidate in vars(module).values()
        if (
            isinstance(candidate, type)
            and candidate.__module__ == module.__name__
            and issubclass(candidate, Category)
            and _is_nullary_category_factory(candidate)
            and not isinstance(getattr(candidate, "super_categories"), AbstractMethod)
            and _has_bound_axiom_metadata(candidate, CategoryWithAxiom)
        )
    )


def _has_bound_axiom_metadata(
    candidate: type[object],
    axiom_base: type[object],
) -> bool:
    if not issubclass(candidate, axiom_base):
        return True
    return "_base_category_class_and_axiom" in candidate.__dict__


def _is_nullary_category_factory(candidate: type[object]) -> bool:
    init_signature = signature(candidate.__init__)
    required_parameters = tuple(
        parameter
        for parameter in tuple(init_signature.parameters.values())[1:]
        if (
            parameter.default is Parameter.empty
            and parameter.kind
            in (
                Parameter.POSITIONAL_ONLY,
                Parameter.POSITIONAL_OR_KEYWORD,
                Parameter.KEYWORD_ONLY,
            )
        )
    )
    return not required_parameters


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
        nargs="*",
        help="Fully-qualified category factory classes to resolve.",
    )
    parser.add_argument(
        "--package",
        action="append",
        default=[],
        help=(
            "Import a module or package tree and discover category classes "
            "defined in it. Pass multiple times for multiple roots."
        ),
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
    unsupported_providers: Iterable[UnsupportedProviderRecord] = (),
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
                *_unsupported_provider_module_names(unsupported_providers),
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


def _unsupported_provider_module_names(
    unsupported_providers: Iterable[UnsupportedProviderRecord],
) -> tuple[str, ...]:
    module_names: list[str] = []
    for unsupported_provider in unsupported_providers:
        for fullname in (
            unsupported_provider.provider,
            *unsupported_provider.runtime_classes,
            *(
                runtime_class
                for runtime_mro in unsupported_provider.runtime_mros
                for runtime_class in runtime_mro
            ),
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


def _external_runtime_class_records(
    *,
    projections: Iterable[ProviderProjection],
    concrete_parents: Iterable[ConcreteParentRecord],
) -> tuple[ExternalRuntimeClassRecord, ...]:
    records: list[ExternalRuntimeClassRecord] = []
    for runtime_class in _external_runtime_class_fullnames(
        projections=projections,
        concrete_parents=concrete_parents,
    ):
        module_name = _importable_module_name_or_none(runtime_class)
        if module_name is None:
            continue
        static_signature_source, source_module = _static_signature_metadata(module_name)
        records.append(
            ExternalRuntimeClassRecord(
                runtime_class=runtime_class,
                module=module_name,
                static_signature_source=static_signature_source,
                source_module=source_module,
            )
        )
    return tuple(records)


def _external_runtime_class_fullnames(
    *,
    projections: Iterable[ProviderProjection],
    concrete_parents: Iterable[ConcreteParentRecord],
) -> tuple[str, ...]:
    fullnames: list[str] = []
    for projection in projections:
        fullnames.extend(projection.unprojected_runtime_mro)
    for concrete_parent in concrete_parents:
        fullnames.extend(concrete_parent.runtime_mro)
        if concrete_parent.element_runtime_class is not None:
            fullnames.append(concrete_parent.element_runtime_class)
    return tuple(
        fullname
        for fullname in dict.fromkeys(fullnames)
        if fullname != "builtins.object"
    )


def _static_signature_metadata(
    module_name: str,
) -> tuple[ExternalRuntimeClassStaticSignatureSource, str | None]:
    source_record = _source_module_record_or_none(module_name)
    if source_record is None:
        return "untyped_external", None

    suffix = Path(source_record.path).suffix
    if suffix == ".py":
        return "python_source", module_name
    if suffix == ".pyi":
        return "stub", module_name
    return "untyped_external", None


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
    if not args.category_fullnames and not args.package and not args.concrete_parent:
        parser.error(
            "provide at least one category fullname, --package, or --concrete-parent"
        )
    roles: tuple[ProviderRole, ...] = (
        ("parent",)
        if not args.role
        else tuple(cast(ProviderRole, role) for role in args.role)
    )
    category_fullnames = tuple(
        dict.fromkeys(
            (
                *discover_category_fullnames(tuple(args.package)),
                *args.category_fullnames,
            )
        )
    )
    write_projection_manifest(
        output=Path(args.output),
        category_fullnames=category_fullnames,
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
