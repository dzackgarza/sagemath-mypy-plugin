from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from sage_mypy_category_plugin.manifest import ProjectionManifest, SourceModuleRecord

type StubTree = dict[str, "StubTree"]


def generated_stub_sources(manifest: ProjectionManifest) -> dict[Path, str]:
    source_modules = tuple(record.module for record in manifest.source_modules)
    assert source_modules, "generated stubs require manifest source_modules"

    module_trees: dict[str, StubTree] = {}
    for provider in _manifest_provider_fullnames(manifest):
        module_name, qualname = _source_module_and_qualname(
            provider,
            source_modules=source_modules,
        )
        module_tree = module_trees.setdefault(module_name, {})
        _add_qualname(module_tree, qualname)

    stub_sources = {
        Path(*module_name.split(".")).with_suffix(".pyi"): _stub_source(tree)
        for module_name, tree in sorted(module_trees.items())
    }
    stub_sources[Path("_sage_category_types.pyi")] = _runtime_alias_stub_source(
        manifest,
        source_modules=source_modules,
    )
    return dict(sorted(stub_sources.items()))


def write_generated_stub_tree(
    output_root: Path,
    manifest: ProjectionManifest,
) -> tuple[SourceModuleRecord, ...]:
    source_modules: list[SourceModuleRecord] = []
    for relative_path, source in generated_stub_sources(manifest).items():
        path = output_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_package_markers(output_root, path.parent)
        path.write_text(source)
        source_bytes = path.read_bytes()
        source_stat = path.stat()
        source_modules.append(
            SourceModuleRecord(
                module=".".join(relative_path.with_suffix("").parts),
                path=str(path),
                sha256=sha256(source_bytes).hexdigest(),
                mtime_ns=source_stat.st_mtime_ns,
            )
        )
    return tuple(source_modules)


def _manifest_provider_fullnames(manifest: ProjectionManifest) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            provider
            for projection in manifest.projections
            for provider in projection.provider_mro
        )
    )


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
                concrete_parent.parent_provider_mro,
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
    provider_mro: tuple[str, ...],
    *,
    source_modules: tuple[str, ...],
    imported_names: dict[str, set[str]],
) -> tuple[str, tuple[str, ...]]:
    assert provider_mro, f"{runtime_class!r} must have a nonempty provider MRO"
    runtime_module, runtime_qualname = _source_module_and_qualname(
        runtime_class,
        source_modules=source_modules,
    )
    return (
        _runtime_alias_name(runtime_module, runtime_qualname),
        tuple(
            _provider_base_expression(
                provider,
                source_modules=source_modules,
                imported_names=imported_names,
            )
            for provider in provider_mro
        ),
    )


def _runtime_alias_name(module_name: str, qualname: tuple[str, ...]) -> str:
    return f"{module_name.replace('.', '_')}__{'__'.join(qualname)}"


def _provider_base_expression(
    provider: str,
    *,
    source_modules: tuple[str, ...],
    imported_names: dict[str, set[str]],
) -> str:
    module_name, qualname = _source_module_and_qualname(
        provider,
        source_modules=source_modules,
    )
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


def _stub_source(tree: StubTree) -> str:
    return "\n".join(_stub_lines(tree)) + "\n"


def _stub_lines(tree: StubTree, indent: int = 0) -> tuple[str, ...]:
    lines: list[str] = []
    for name, child in sorted(
        tree.items(),
        key=lambda item: (item[0] not in {"ParentMethods", "ElementMethods"}, item[0]),
    ):
        lines.append(f"{'    ' * indent}class {name}:")
        if child:
            lines.extend(_stub_lines(child, indent + 1))
        else:
            lines.append(f"{'    ' * (indent + 1)}...")
    return tuple(lines)


def _write_package_markers(output_root: Path, package_dir: Path) -> None:
    current = package_dir
    packages: list[Path] = []
    while current != output_root:
        packages.append(current)
        current = current.parent
    for package in reversed(packages):
        (package / "__init__.pyi").write_text("")


__all__ = ["generated_stub_sources", "write_generated_stub_tree"]
