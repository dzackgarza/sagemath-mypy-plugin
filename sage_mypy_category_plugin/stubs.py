from __future__ import annotations

from pathlib import Path

from sage_mypy_category_plugin.manifest import ProjectionManifest

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

    return {
        Path(*module_name.split(".")).with_suffix(".pyi"): _stub_source(tree)
        for module_name, tree in sorted(module_trees.items())
    }


def _manifest_provider_fullnames(manifest: ProjectionManifest) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            provider
            for projection in manifest.projections
            for provider in projection.provider_mro
        )
    )


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


__all__ = ["generated_stub_sources"]
