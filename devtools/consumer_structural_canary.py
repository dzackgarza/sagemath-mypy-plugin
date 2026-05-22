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
    "subcategory",
    "morphism",
    "homset_parent",
    "homset_element",
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
CONSUMER_PROVIDER_PREFIX = "category_specs."


@dataclass(frozen=True)
class CanaryPaths:
    config_path: Path
    cache_dir: Path
    mypy_cache_dir: Path
    negative_probe_path: Path


@dataclass(frozen=True)
class StructuralAudit:
    checked_provider_count: int
    graph_absent_provider_count: int
    missing_typeinfo_count: int


@dataclass(frozen=True)
class BuildPlan:
    mode: str
    sources: tuple[BuildSource, ...]
    requires_all_graph_providers: bool


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
        negative_probe_path=work_dir / "negative_consumer_probe.py",
    )
    _write_config(paths)
    _write_negative_probe(paths)
    build_plan = _with_negative_probe(
        _consumer_build_plan(consumer_root, all_modules=args.all_consumer_modules),
        paths,
    )
    result = _build_consumer_modules(paths, consumer_root, build_plan)
    manifest_path = paths.cache_dir / "projection-manifest.json"
    manifest = load_manifest(manifest_path)

    _assert_manifest_has_no_generated_stub_cache(paths)
    negative_error_count = _assert_negative_probe_error_survives(result, paths)
    structural_audit = _assert_provider_typeinfos_match_manifest(
        result,
        manifest,
        require_all_graph_providers=build_plan.requires_all_graph_providers,
    )

    print(f"consumer_root={consumer_root}")
    print(f"work_dir={work_dir}")
    print(f"manifest={manifest_path}")
    print(f"source_mode={build_plan.mode}")
    print(f"source_module_count={len(build_plan.sources)}")
    print(f"manifest_source_module_count={len(manifest.source_modules)}")
    print(f"projection_count={len(manifest.projections)}")
    print(f"unsupported_provider_count={len(manifest.unsupported_providers)}")
    print(f"checked_provider_count={structural_audit.checked_provider_count}")
    print(f"graph_absent_provider_count={structural_audit.graph_absent_provider_count}")
    print(f"missing_typeinfo_count={structural_audit.missing_typeinfo_count}")
    print(f"negative_injected_error_count={negative_error_count}")
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
    parser.add_argument(
        "--all-consumer-modules",
        action="store_true",
        help=(
            "Build every Python module under category_specs instead of the "
            "fast representative module set."
        ),
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


def _write_negative_probe(paths: CanaryPaths) -> None:
    paths.negative_probe_path.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "",
                "from category_specs.sets import _SetObjectMethods",
                "",
                "bad_assignment: _SetObjectMethods = 1",
                "",
            )
        ),
        encoding="utf-8",
    )


def _build_consumer_modules(
    paths: CanaryPaths,
    consumer_root: Path,
    build_plan: BuildPlan,
) -> BuildResult:
    options = Options()
    options.config_file = str(paths.config_path)
    options.plugins = ["sage_mypy_category_plugin.plugin"]
    options.incremental = False
    options.cache_dir = str(paths.mypy_cache_dir)
    options.mypy_path = [str(REPO_ROOT), str(consumer_root)]
    options.ignore_missing_imports = True
    options.explicit_package_bases = True

    return build(sources=list(build_plan.sources), options=options)


def _consumer_build_plan(consumer_root: Path, *, all_modules: bool) -> BuildPlan:
    if all_modules:
        return BuildPlan(
            mode="all",
            sources=_all_category_specs_sources(consumer_root),
            requires_all_graph_providers=True,
        )
    return BuildPlan(
        mode="representative",
        sources=tuple(
            BuildSource(str(_module_path(consumer_root, module)), module, None)
            for module in CANARY_MODULES
        ),
        requires_all_graph_providers=False,
    )


def _with_negative_probe(
    build_plan: BuildPlan,
    paths: CanaryPaths,
) -> BuildPlan:
    return BuildPlan(
        mode=build_plan.mode,
        sources=(
            *build_plan.sources,
            BuildSource(
                str(paths.negative_probe_path),
                "_sage_mypy_category_specs_negative_probe",
                None,
            ),
        ),
        requires_all_graph_providers=build_plan.requires_all_graph_providers,
    )


def _all_category_specs_sources(consumer_root: Path) -> tuple[BuildSource, ...]:
    package_root = consumer_root / "category_specs"
    sources = tuple(
        BuildSource(str(path), _module_name_for_path(consumer_root, path), None)
        for path in sorted(package_root.rglob("*.py"))
        if "__pycache__" not in path.parts
    )
    if not sources:
        raise SystemExit(f"No category_specs Python modules found under {package_root}")
    return sources


def _module_name_for_path(consumer_root: Path, path: Path) -> str:
    relative = path.relative_to(consumer_root)
    if relative.name == "__init__.py":
        return ".".join(relative.parent.parts)
    return ".".join(relative.with_suffix("").parts)


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


def _assert_negative_probe_error_survives(
    result: BuildResult,
    paths: CanaryPaths,
) -> int:
    probe_name = paths.negative_probe_path.name
    probe_errors = tuple(error for error in result.errors if probe_name in error)
    if not probe_errors:
        raise AssertionError(
            "negative consumer probe produced no mypy errors; "
            "the canary no longer proves ordinary consumer diagnostics survive"
        )
    assignment_errors = tuple(error for error in probe_errors if "[assignment]" in error)
    if not assignment_errors:
        raise AssertionError(
            "negative consumer probe errors did not include the expected "
            f"[assignment] diagnostic: {probe_errors!r}"
        )
    return len(probe_errors)


def _assert_provider_typeinfos_match_manifest(
    result: BuildResult,
    manifest: ProjectionManifest,
    *,
    require_all_graph_providers: bool,
) -> StructuralAudit:
    checked_provider_count = 0
    graph_absent_provider_count = 0
    missing_typeinfos: list[str] = []
    source_modules = tuple(record.module for record in manifest.source_modules)
    for projection in manifest.projections:
        provider = projection.provider
        if not provider.startswith(CONSUMER_PROVIDER_PREFIX):
            continue
        provider_module = _source_module_for_fullname(source_modules, provider)
        if provider_module is None or provider_module not in result.graph:
            graph_absent_provider_count += 1
            continue
        info = _typeinfo_for_fullname(result, provider, provider_module)
        if info is None:
            missing_typeinfos.append(provider)
            continue
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
        checked_provider_count += 1

    if checked_provider_count == 0:
        raise AssertionError("No category_specs provider TypeInfos were checked")
    if require_all_graph_providers and graph_absent_provider_count:
        raise AssertionError(
            "Full consumer structural canary left "
            f"{graph_absent_provider_count} projected category_specs providers "
            "outside the mypy graph"
        )
    if missing_typeinfos:
        missing = "\n  ".join(missing_typeinfos)
        raise AssertionError(f"Missing TypeInfo for loaded providers:\n  {missing}")

    return StructuralAudit(
        checked_provider_count=checked_provider_count,
        graph_absent_provider_count=graph_absent_provider_count,
        missing_typeinfo_count=len(missing_typeinfos),
    )


def _typeinfo_for_fullname(
    result: BuildResult,
    fullname: str,
    module_name: str,
) -> TypeInfo | None:
    state = result.graph[module_name]
    if state.tree is None:
        return None
    suffix = fullname.removeprefix(f"{module_name}.")
    pieces = suffix.split(".")
    symbol = state.tree.names.get(pieces[0])
    if symbol is None or not isinstance(symbol.node, TypeInfo):
        return None
    info = symbol.node
    for piece in pieces[1:]:
        nested = info.names.get(piece)
        if nested is None or not isinstance(nested.node, TypeInfo):
            return None
        info = nested.node
    return info


def _source_module_for_fullname(
    source_modules: tuple[str, ...],
    fullname: str,
) -> str | None:
    matches = [
        module
        for module in source_modules
        if fullname == module or fullname.startswith(f"{module}.")
    ]
    if not matches:
        return None
    return max(matches, key=len)


if __name__ == "__main__":
    main()
