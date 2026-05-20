from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path

from sage_mypy_category_plugin.manifest import (
    ProjectionManifest,
    SourceModuleRecord,
    load_manifest,
    write_manifest,
)
from sage_mypy_category_plugin.projection import ProviderMethodRecord
from sage_mypy_category_plugin.static_stubs import (
    static_stub_modules,
    static_stub_sources,
)

type StubTree = dict[str, "StubTree"]
type ProviderMethodMap = dict[
    tuple[str, tuple[str, ...]],
    tuple[ProviderMethodRecord, ...],
]
type ClassBaseMap = dict[tuple[str, tuple[str, ...]], tuple[str, ...]]
type StubOrder = dict[tuple[str, tuple[str, ...]], int]
METHOD_PROVIDER_NAMES = frozenset(
    ("ParentMethods", "ElementMethods", "SubcategoryMethods", "MorphismMethods")
)
MODULE_STUB_SUFFIXES: dict[Path, str] = {
    Path("sage/categories/homsets.pyi"): (
        "\n"
        "class HomsetsCategory:\n"
        "    ...\n"
        "\n"
        "class HomsetsOf(HomsetsCategory):\n"
        "    ...\n"
    ),
}


def generated_stub_sources(
    manifest: ProjectionManifest,
    *,
    preserved_source_module_prefixes: Sequence[str] = (),
) -> dict[Path, str]:
    source_modules = tuple(record.module for record in manifest.source_modules)
    assert source_modules, "generated stubs require manifest source_modules"
    preserved_prefixes = tuple(
        dict.fromkeys((*preserved_source_module_prefixes, *static_stub_modules()))
    )

    module_trees: dict[str, StubTree] = {}
    for fullname in _manifest_stub_fullnames(manifest):
        module_name, qualname = _source_module_and_qualname(
            fullname,
            source_modules=source_modules,
        )
        module_tree = module_trees.setdefault(module_name, {})
        _add_qualname(module_tree, qualname)
    provider_stub_modules = frozenset(module_trees)
    untyped_external_classes = _untyped_external_stub_classes(manifest)
    for module_name, qualname in untyped_external_classes:
        module_tree = module_trees.setdefault(module_name, {})
        _add_qualname(module_tree, qualname)
    untyped_external_only_modules = frozenset(
        module_name
        for module_name, _ in untyped_external_classes
        if module_name not in provider_stub_modules
    )
    provider_methods = _provider_methods_by_owner(
        manifest.provider_methods,
        source_modules=source_modules,
    )
    class_bases = _stub_class_bases(
        manifest,
        source_modules=source_modules,
    )
    for module_name, qualname in provider_methods:
        module_tree = module_trees.setdefault(module_name, {})
        _add_qualname(module_tree, qualname)
    stub_order = _stub_order(manifest, source_modules=source_modules)

    stub_sources = {
        Path(*module_name.split(".")).with_suffix(".pyi"): _stub_source(
            tree,
            module_name=module_name,
            provider_methods=provider_methods,
            class_bases=class_bases,
            source_modules=source_modules,
            stub_order=stub_order,
        )
        for module_name, tree in sorted(module_trees.items())
        if (
            not _is_preserved_source_module(module_name, preserved_prefixes)
            or module_name in untyped_external_only_modules
        )
    }
    for relative_path, suffix in MODULE_STUB_SUFFIXES.items():
        if relative_path in stub_sources:
            stub_sources[relative_path] = stub_sources[relative_path].rstrip() + suffix
    stub_sources[Path("_sage_category_types.pyi")] = _runtime_alias_stub_source(
        manifest,
        source_modules=source_modules,
    )
    return dict(sorted(stub_sources.items()))


def write_generated_stub_tree(
    output_root: Path,
    manifest: ProjectionManifest,
    *,
    preserved_source_module_prefixes: Sequence[str] = (),
) -> tuple[SourceModuleRecord, ...]:
    preserved_prefixes = tuple(
        dict.fromkeys((*preserved_source_module_prefixes, *static_stub_modules()))
    )
    external_runtime_source_modules = frozenset(
        record.source_module
        for record in manifest.external_runtime_classes
        if record.source_module is not None
    )
    original_source_module_by_module = manifest.source_module_by_module
    source_modules: list[SourceModuleRecord] = []
    declared_source_modules: set[str] = set()
    source_module_index_by_module: dict[str, int] = {}
    for record in manifest.source_modules:
        if _is_preserved_source_module(record.module, preserved_prefixes):
            source_module_index_by_module[record.module] = len(source_modules)
            source_modules.append(record)
            declared_source_modules.add(record.module)

    # Write static stubs FIRST so generated stubs can override them for
    # untyped_external classes (which need shell stubs, not rich signatures).
    for relative_path, source in static_stub_sources().items():
        path = output_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
        if relative_path.name == "__init__.pyi":
            continue
        source_bytes = path.read_bytes()
        source_stat = path.stat()
        module_name = ".".join(relative_path.with_suffix("").parts)
        record = SourceModuleRecord(
            module=module_name,
            path=str(path),
            sha256=sha256(source_bytes).hexdigest(),
            mtime_ns=source_stat.st_mtime_ns,
        )
        existing_index = source_module_index_by_module.get(module_name)
        if existing_index is None:
            source_module_index_by_module[module_name] = len(source_modules)
            source_modules.append(record)
        else:
            source_modules[existing_index] = record
        declared_source_modules.add(module_name)

    # Write generated stubs SECOND so they override static stubs for any module
    # that has untyped_external classes (shell stubs take precedence).
    for relative_path, source in generated_stub_sources(
        manifest,
        preserved_source_module_prefixes=preserved_prefixes,
    ).items():
        path = output_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_package_markers(output_root, path.parent)
        path.write_text(source)
        if relative_path.name == "__init__.pyi":
            continue
        source_bytes = path.read_bytes()
        source_stat = path.stat()
        module_name = ".".join(relative_path.with_suffix("").parts)
        record = SourceModuleRecord(
            module=module_name,
            path=str(path),
            sha256=sha256(source_bytes).hexdigest(),
            mtime_ns=source_stat.st_mtime_ns,
        )
        existing_index = source_module_index_by_module.get(module_name)
        if existing_index is None:
            source_module_index_by_module[module_name] = len(source_modules)
            source_modules.append(record)
        else:
            source_modules[existing_index] = record
        declared_source_modules.add(module_name)
    for module_name in sorted(external_runtime_source_modules):
        if module_name in declared_source_modules:
            continue
        source_module_index_by_module[module_name] = len(source_modules)
        source_modules.append(original_source_module_by_module[module_name])
        declared_source_modules.add(module_name)
    return tuple(source_modules)


def _is_preserved_source_module(module_name: str, prefixes: Sequence[str]) -> bool:
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for prefix in prefixes
    )


def _stub_argument_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="sage_mypy_category_plugin.stubs",
        description="Generate mypy-visible Sage category stubs from a manifest.",
    )
    parser.add_argument(
        "manifest",
        help="Path to read ProjectionManifest JSON.",
    )
    parser.add_argument(
        "output_root",
        help="Directory where generated .pyi files are written.",
    )
    parser.add_argument(
        "--manifest-output",
        help=(
            "Optional path to write a manifest whose source metadata points at "
            "the generated stub tree."
        ),
    )
    parser.add_argument(
        "--preserve-source-module-prefix",
        action="append",
        default=[],
        dest="preserved_source_module_prefixes",
        metavar="MODULE",
        help=(
            "Keep matching source modules in the emitted manifest and do not "
            "write their generated .pyi files. Pass multiple times for multiple "
            "module prefixes."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _stub_argument_parser().parse_args(argv)
    manifest = load_manifest(Path(args.manifest))
    source_modules = write_generated_stub_tree(
        Path(args.output_root),
        manifest,
        preserved_source_module_prefixes=args.preserved_source_module_prefixes,
    )
    if args.manifest_output is not None:
        write_manifest(
            Path(args.manifest_output),
            manifest.model_copy(update={"source_modules": source_modules}),
        )
    return 0


def _manifest_stub_fullnames(manifest: ProjectionManifest) -> tuple[str, ...]:
    fullnames: list[str] = []
    for projection in manifest.projections:
        fullnames.extend(projection.provider_mro)
    for record in manifest.concrete_parents:
        fullnames.append(record.concrete_class)
    return tuple(dict.fromkeys(fullnames))


def _untyped_external_stub_classes(
    manifest: ProjectionManifest,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple(
        _external_runtime_module_and_qualname(record.runtime_class, module=record.module)
        for record in manifest.external_runtime_classes
        if record.static_signature_source == "untyped_external"
    )


def _external_runtime_module_and_qualname(
    runtime_class: str,
    *,
    module: str,
) -> tuple[str, tuple[str, ...]]:
    assert runtime_class.startswith(f"{module}."), (
        f"External runtime class {runtime_class!r} is not in module {module!r}"
    )
    qualname = tuple(runtime_class[len(module) + 1 :].split("."))
    assert qualname, f"External runtime class {runtime_class!r} needs a qualname"
    return module, qualname


def _stub_order(
    manifest: ProjectionManifest,
    *,
    source_modules: tuple[str, ...],
) -> StubOrder:
    order: StubOrder = {}
    for fullname in _provider_fullnames_in_dependency_order(manifest):
        module_name, qualname = _source_module_and_qualname(
            fullname,
            source_modules=source_modules,
        )
        for prefix_length in range(1, len(qualname) + 1):
            order.setdefault((module_name, qualname[:prefix_length]), len(order))
    return order


def _provider_fullnames_in_dependency_order(
    manifest: ProjectionManifest,
) -> tuple[str, ...]:
    ordered_fullnames: list[str] = []
    seen_fullnames: set[str] = set()
    for projection in manifest.projections:
        for fullname in reversed(projection.provider_mro):
            if fullname not in seen_fullnames:
                ordered_fullnames.append(fullname)
                seen_fullnames.add(fullname)
    return tuple(ordered_fullnames)


def _provider_methods_by_owner(
    provider_methods: tuple[ProviderMethodRecord, ...],
    *,
    source_modules: tuple[str, ...],
) -> ProviderMethodMap:
    methods_by_owner: dict[tuple[str, tuple[str, ...]], list[ProviderMethodRecord]] = {}
    for provider_method in provider_methods:
        owner = _source_module_and_qualname(
            provider_method.provider,
            source_modules=source_modules,
        )
        methods_by_owner.setdefault(owner, []).append(provider_method)
    return {
        owner: tuple(sorted(methods, key=lambda method: method.name))
        for owner, methods in methods_by_owner.items()
    }


def _stub_class_bases(
    manifest: ProjectionManifest,
    *,
    source_modules: tuple[str, ...],
) -> ClassBaseMap:
    # Provider bases are injected at analysis time by the plugin — they must
    # not appear in generated stubs, or without-plugin runs would see them and
    # not raise [attr-defined] for methods that come from the injected MRO.
    # Only concrete_parent bases (runtime alias → provider MRO) go into stubs.
    return {
        _source_module_and_qualname(
            concrete_parent.concrete_class,
            source_modules=source_modules,
        ): concrete_parent.parent_provider_mro
        for concrete_parent in manifest.concrete_parents
    }


def _runtime_alias_stub_source(
    manifest: ProjectionManifest,
    *,
    source_modules: tuple[str, ...],
) -> str:
    imported_names: dict[str, set[str]] = {}
    alias_blocks: list[tuple[str, tuple[str, ...]]] = []
    for projection in manifest.projections:
        alias_blocks.append(
            _runtime_alias_block(
                projection.runtime_class,
                projection.provider_mro,
                source_modules=source_modules,
                imported_names=imported_names,
            )
        )
    for concrete_parent in manifest.concrete_parents:
        alias_blocks.append(
            _runtime_alias_block(
                concrete_parent.runtime_class,
                (
                    concrete_parent.concrete_class,
                    *concrete_parent.parent_provider_mro,
                ),
                source_modules=source_modules,
                imported_names=imported_names,
            )
        )
        if concrete_parent.element_runtime_class is not None:
            alias_blocks.append(
                _runtime_alias_block(
                    concrete_parent.element_runtime_class,
                    concrete_parent.element_provider_mro,
                    source_modules=source_modules,
                    imported_names=imported_names,
                )
            )

    lines: list[str] = []
    for module_name, names in sorted(imported_names.items()):
        lines.append(f"from {module_name} import {', '.join(sorted(names))}")
    lines.append("")
    for alias_name, provider_bases in sorted(alias_blocks):
        lines.append(f"class {alias_name}(")
        lines.extend(f"    {provider_base}," for provider_base in provider_bases)
        lines.append("):")
        lines.append("    ...")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _runtime_alias_block(
    runtime_class: str,
    base_fullnames: tuple[str, ...],
    *,
    source_modules: tuple[str, ...],
    imported_names: dict[str, set[str]],
) -> tuple[str, tuple[str, ...]]:
    assert base_fullnames, f"{runtime_class!r} must have a nonempty alias base list"
    runtime_module, runtime_qualname = _source_module_and_qualname(
        runtime_class,
        source_modules=source_modules,
    )
    return (
        _runtime_alias_name(runtime_module, runtime_qualname),
        tuple(
            _base_expression(
                fullname,
                source_modules=source_modules,
                imported_names=imported_names,
                current_module=None,
            )
            for fullname in base_fullnames
        ),
    )


def _runtime_alias_name(module_name: str, qualname: tuple[str, ...]) -> str:
    return f"{module_name.replace('.', '_')}__{'__'.join(qualname)}"


def _base_expression(
    fullname: str,
    *,
    source_modules: tuple[str, ...],
    imported_names: dict[str, set[str]],
    current_module: str | None,
) -> str:
    module_name, qualname = _source_module_and_qualname(
        fullname,
        source_modules=source_modules,
    )
    if module_name != current_module:
        imported_names.setdefault(module_name, set()).add(qualname[0])
    return ".".join(qualname)


def _source_module_and_qualname(
    provider: str,
    *,
    source_modules: tuple[str, ...],
) -> tuple[str, tuple[str, ...]]:
    matching_modules = tuple(
        module for module in source_modules if provider.startswith(f"{module}.")
    )
    assert matching_modules, (
        f"Provider {provider!r} is not covered by manifest source_modules"
    )

    module_name = max(matching_modules, key=len)
    qualname = tuple(provider[len(module_name) + 1 :].split("."))
    assert qualname, f"Provider {provider!r} must include a class qualname"
    return module_name, qualname


def _add_qualname(tree: StubTree, qualname: tuple[str, ...]) -> None:
    current = tree
    for name in qualname:
        current = current.setdefault(name, {})


def _stub_source(
    tree: StubTree,
    *,
    module_name: str,
    provider_methods: ProviderMethodMap,
    class_bases: ClassBaseMap,
    source_modules: tuple[str, ...],
    stub_order: StubOrder,
) -> str:
    imported_names: dict[str, set[str]] = {}
    body_lines = _stub_lines(
        tree,
        module_name=module_name,
        provider_methods=provider_methods,
        class_bases=class_bases,
        source_modules=source_modules,
        stub_order=stub_order,
        imported_names=imported_names,
    )
    import_lines = _source_import_lines(
        module_name,
        provider_methods=provider_methods,
        imported_names=imported_names,
    )
    if import_lines:
        return "\n".join((*import_lines, "", *body_lines)) + "\n"
    return "\n".join(body_lines) + "\n"


def _source_import_lines(
    module_name: str,
    *,
    provider_methods: ProviderMethodMap,
    imported_names: dict[str, set[str]],
) -> tuple[str, ...]:
    lines: list[str] = []
    if _module_uses_self_return(module_name, provider_methods):
        lines.append("from typing import Self")
    lines.extend(
        f"from {imported_module} import {', '.join(sorted(names))}"
        for imported_module, names in sorted(imported_names.items())
    )
    return tuple(lines)


def _module_uses_self_return(
    module_name: str,
    provider_methods: ProviderMethodMap,
) -> bool:
    return any(
        method.return_type == "Self"
        for (method_module, _), methods in provider_methods.items()
        if method_module == module_name
        for method in methods
    )


def _stub_lines(
    tree: StubTree,
    *,
    module_name: str,
    provider_methods: ProviderMethodMap,
    class_bases: ClassBaseMap,
    source_modules: tuple[str, ...],
    stub_order: StubOrder,
    imported_names: dict[str, set[str]],
    qualname: tuple[str, ...] = (),
    indent: int = 0,
) -> tuple[str, ...]:
    lines: list[str] = []
    for name, child in sorted(
        tree.items(),
        key=lambda item: _stub_sort_key(
            item[0],
            module_name=module_name,
            qualname=qualname,
            stub_order=stub_order,
        ),
    ):
        nested_qualname = (*qualname, name)
        methods = provider_methods.get((module_name, nested_qualname), ())
        base_fullnames = class_bases.get((module_name, nested_qualname), ())
        base_expressions = tuple(
            _base_expression(
                fullname,
                source_modules=source_modules,
                imported_names=imported_names,
                current_module=module_name,
            )
            for fullname in base_fullnames
        )
        class_indent = "    " * indent
        if base_expressions:
            lines.append(f"{class_indent}class {name}(")
            lines.extend(f"{class_indent}    {base}," for base in base_expressions)
            lines.append(f"{class_indent}):")
        else:
            lines.append(f"{class_indent}class {name}:")
        method_indent = "    " * (indent + 1)
        for method in methods:
            param_str = ", ".join(("self", *method.params))
            lines.append(
                f"{method_indent}def {method.name}({param_str}) -> {method.return_type}: ..."
            )
        if child:
            lines.extend(
                _stub_lines(
                    child,
                    module_name=module_name,
                    provider_methods=provider_methods,
                    class_bases=class_bases,
                    source_modules=source_modules,
                    stub_order=stub_order,
                    imported_names=imported_names,
                    qualname=nested_qualname,
                    indent=indent + 1,
                )
            )
        elif not methods:
            lines.append(f"{'    ' * (indent + 1)}...")
    return tuple(lines)


def _stub_sort_key(
    name: str,
    *,
    module_name: str,
    qualname: tuple[str, ...],
    stub_order: StubOrder,
) -> tuple[bool, int, str]:
    nested_qualname = (*qualname, name)
    if name in METHOD_PROVIDER_NAMES:
        return (False, 0, name)
    return (
        True,
        stub_order.get((module_name, nested_qualname), len(stub_order)),
        name,
    )


def _write_package_markers(output_root: Path, package_dir: Path) -> None:
    current = package_dir
    packages: list[Path] = []
    while current != output_root:
        packages.append(current)
        current = current.parent
    for package in reversed(packages):
        (package / "__init__.pyi").write_text("")


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "generated_stub_sources",
    "main",
    "write_generated_stub_tree",
]
