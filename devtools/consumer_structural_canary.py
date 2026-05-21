from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from mypy.build import BuildResult, BuildSource, build
from mypy.nodes import TypeInfo
from mypy.options import Options

from sage_mypy_category_plugin.manifest import ProjectionManifest, load_manifest


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONSUMER_ROOT = Path("/home/dzack/research")
DEFAULT_WORK_DIR = Path(".mypy_cache/sage-category-plugin-consumer-canary")
DEFAULT_ROLES = (
    "parent",
    "element",
)
CANARY_MODULES = (
    "category_specs.cat",
    "category_specs.rings",
    "category_specs.sets",
    "category_specs.topological_spaces",
)
CANARY_PROVIDERS = (
    "category_specs.cat._CatObjectMethods",
    "category_specs.cat._CategoryElementMethods",
    "category_specs.rings._RingObjectMethods",
    "category_specs.rings._RingElementMethods",
    "category_specs.sets._SetObjectMethods",
    "category_specs.sets._SetElementMethods",
    "category_specs.topological_spaces._TopologicalSpaceObjectMethods",
    "category_specs.topological_spaces._TopologicalSpaceElementMethods",
)


@dataclass(frozen=True)
class CanaryPaths:
    config_path: Path
    cache_dir: Path
    mypy_cache_dir: Path


def main() -> None:
    args = _parse_args()
    consumer_root = args.consumer_root.resolve()
    consumer_package = consumer_root / "category_specs"
    if not consumer_package.is_dir():
        raise SystemExit(f"category_specs consumer tree not found at {consumer_package}")

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    if str(consumer_root) not in sys.path:
        sys.path.insert(0, str(consumer_root))

    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    paths = CanaryPaths(
        config_path=work_dir / "mypy.ini",
        cache_dir=work_dir / "sage-category-cache",
        mypy_cache_dir=work_dir / "mypy-cache",
    )
    _write_config(paths)
    result = _build_consumer_modules(paths, consumer_root)
    manifest_path = paths.cache_dir / "projection-manifest.json"
    manifest = load_manifest(manifest_path)

    _assert_manifest_has_no_generated_stub_cache(paths)
    _assert_provider_typeinfos_match_manifest(result, manifest)

    print(f"consumer_root={consumer_root}")
    print(f"work_dir={work_dir}")
    print(f"manifest={manifest_path}")
    print(f"projection_count={len(manifest.projections)}")
    print(f"unsupported_provider_count={len(manifest.unsupported_providers)}")
    print(f"mypy_error_count={len(result.errors)}")
    for provider in CANARY_PROVIDERS:
        projection = manifest.projection_by_provider[provider]
        print(
            f"ok {provider}: bases={len(projection.provider_bases)} "
            f"mro={len(projection.provider_mro)}"
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify real category_specs provider TypeInfos against the plugin-owned "
            "projection manifest."
        )
    )
    parser.add_argument(
        "--consumer-root",
        type=Path,
        default=DEFAULT_CONSUMER_ROOT,
        help="Directory containing the category_specs package.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=DEFAULT_WORK_DIR,
        help="Directory where canary config, mypy cache, and manifest are retained.",
    )
    return parser.parse_args()


def _write_config(paths: CanaryPaths) -> None:
    paths.config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "ignore_missing_imports = True",
                "explicit_package_bases = True",
                "",
                "[sage-mypy-category-plugin]",
                "packages = category_specs",
                "roles =",
                *[f"    {role}" for role in DEFAULT_ROLES],
                f"cache_dir = {paths.cache_dir}",
                "strict = true",
                "",
            )
        ),
        encoding="utf-8",
    )


def _build_consumer_modules(paths: CanaryPaths, consumer_root: Path) -> BuildResult:
    options = Options()
    options.config_file = str(paths.config_path)
    options.plugins = ["sage_mypy_category_plugin.plugin"]
    options.incremental = False
    options.cache_dir = str(paths.mypy_cache_dir)
    options.mypy_path = [str(REPO_ROOT), str(consumer_root)]
    options.ignore_missing_imports = True
    options.explicit_package_bases = True

    return build(
        sources=[
            BuildSource(str(_module_path(consumer_root, module)), module, None)
            for module in CANARY_MODULES
        ],
        options=options,
    )


def _module_path(consumer_root: Path, module: str) -> Path:
    relative = Path(*module.split("."))
    package_path = consumer_root / relative / "__init__.py"
    if package_path.is_file():
        return package_path
    module_path = consumer_root / relative.with_suffix(".py")
    if module_path.is_file():
        return module_path
    raise SystemExit(f"Cannot resolve canary module {module!r} under {consumer_root}")


def _assert_manifest_has_no_generated_stub_cache(paths: CanaryPaths) -> None:
    if not (paths.cache_dir / "projection-manifest.json").is_file():
        raise AssertionError("plugin did not write projection-manifest.json")
    if (paths.cache_dir / "stubs").exists():
        raise AssertionError("production package mode generated cache stubs")


def _assert_provider_typeinfos_match_manifest(
    result: BuildResult,
    manifest: ProjectionManifest,
) -> None:
    projection_by_provider = manifest.projection_by_provider
    for provider in CANARY_PROVIDERS:
        projection = projection_by_provider[provider]
        info = _typeinfo_for_fullname(result, provider)
        observed_bases = tuple(base.type.fullname for base in info.bases)
        observed_mro = tuple(
            mro_info.fullname
            for mro_info in info.mro
            if mro_info.fullname != "builtins.object"
        )
        if observed_bases != projection.provider_bases:
            raise AssertionError(
                f"{provider} TypeInfo.bases mismatch: "
                f"expected {projection.provider_bases!r}, observed {observed_bases!r}"
            )
        if observed_mro != projection.provider_mro:
            raise AssertionError(
                f"{provider} TypeInfo.mro mismatch: "
                f"expected {projection.provider_mro!r}, observed {observed_mro!r}"
            )


def _typeinfo_for_fullname(result: BuildResult, fullname: str) -> TypeInfo:
    module_name = _longest_graph_module_prefix(result, fullname)
    state = result.graph[module_name]
    suffix = fullname.removeprefix(f"{module_name}.")
    pieces = suffix.split(".")
    symbol = state.tree.names.get(pieces[0])
    if symbol is None or not isinstance(symbol.node, TypeInfo):
        raise AssertionError(f"Missing TypeInfo for {pieces[0]!r} in {module_name}")
    info = symbol.node
    for piece in pieces[1:]:
        nested = info.names.get(piece)
        if nested is None or not isinstance(nested.node, TypeInfo):
            raise AssertionError(f"Missing nested TypeInfo {piece!r} in {info.fullname}")
        info = nested.node
    return info


def _longest_graph_module_prefix(result: BuildResult, fullname: str) -> str:
    matches = [
        module
        for module in result.graph
        if fullname == module or fullname.startswith(f"{module}.")
    ]
    if not matches:
        raise AssertionError(f"No mypy graph module contains {fullname!r}")
    return max(matches, key=len)


if __name__ == "__main__":
    main()
