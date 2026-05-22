from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from mypy.build import BuildResult, BuildSource, build
from mypy.nodes import TypeInfo
from mypy.options import Options

from sage_mypy_category_plugin.manifest import ProjectionManifest, load_manifest
from sage_mypy_category_plugin.projection import ProviderProjection


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONSUMER_ROOT = Path("/home/dzack/research")
DEFAULT_WORK_DIR = Path(".mypy_cache/sage-category-plugin-consumer-canary")
DEFAULT_ARTIFACT_DIR = Path("artifacts/consumer-structural")
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
    projection_trace_path: Path


@dataclass(frozen=True)
class StructuralAudit:
    checked_provider_count: int
    graph_absent_provider_count: int
    missing_typeinfo_count: int
    projected_ancestor_missing_typeinfo_count: int
    mismatched_provider_count: int
    checked_providers: tuple[str, ...]
    graph_absent_providers: tuple[str, ...]
    missing_typeinfos: tuple[str, ...]
    projected_ancestor_missing_typeinfos: tuple[ProjectedAncestorMissing, ...]
    mismatches: tuple[ProviderMismatch, ...]


@dataclass(frozen=True)
class ProjectedAncestorMissing:
    provider: str
    ancestor: str
    reason: str


@dataclass(frozen=True)
class ProviderMismatch:
    provider: str
    field: str
    expected: tuple[str, ...]
    observed: tuple[str, ...]


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
        projection_trace_path=work_dir / "projection-hook-trace.jsonl",
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

    generated_stub_cache_absent = _manifest_has_no_generated_stub_cache(paths)
    negative_error_count = _negative_probe_error_count(result, paths)
    structural_audit = _provider_typeinfos_audit(
        result,
        manifest,
    )
    artifact_dir = args.artifact_dir.resolve()
    _write_artifacts(
        artifact_dir=artifact_dir,
        paths=paths,
        consumer_root=consumer_root,
        build_plan=build_plan,
        result=result,
        manifest=manifest,
        structural_audit=structural_audit,
        generated_stub_cache_absent=generated_stub_cache_absent,
        negative_error_count=negative_error_count,
    )

    _assert_manifest_has_no_generated_stub_cache(generated_stub_cache_absent)
    _assert_negative_probe_error_survives(negative_error_count, result, paths)
    _assert_provider_typeinfos_match_manifest(
        structural_audit,
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
    print(
        "projected_ancestor_missing_typeinfo_count="
        f"{structural_audit.projected_ancestor_missing_typeinfo_count}"
    )
    print(f"mismatched_provider_count={structural_audit.mismatched_provider_count}")
    print(f"negative_injected_error_count={negative_error_count}")
    print(f"artifact_dir={artifact_dir}")
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
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=DEFAULT_ARTIFACT_DIR,
        help=(
            "Repo-local directory where durable JSON and Markdown diagnostics "
            "are written for external analysis."
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
                f"trace_path = {paths.projection_trace_path}",
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


def _manifest_has_no_generated_stub_cache(paths: CanaryPaths) -> bool:
    return (paths.cache_dir / "projection-manifest.json").is_file() and not (
        paths.cache_dir / "stubs"
    ).exists()


def _assert_manifest_has_no_generated_stub_cache(
    generated_stub_cache_absent: bool,
) -> None:
    if not generated_stub_cache_absent:
        raise AssertionError(
            "plugin did not write projection-manifest.json or generated cache stubs"
        )


def _negative_probe_error_count(
    result: BuildResult,
    paths: CanaryPaths,
) -> int:
    probe_name = paths.negative_probe_path.name
    probe_errors = tuple(error for error in result.errors if probe_name in error)
    return len(probe_errors)


def _assert_negative_probe_error_survives(
    negative_error_count: int,
    result: BuildResult,
    paths: CanaryPaths,
) -> None:
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
    if negative_error_count != len(probe_errors):
        raise AssertionError("negative probe artifact count disagrees with result errors")


def _provider_typeinfos_audit(
    result: BuildResult,
    manifest: ProjectionManifest,
) -> StructuralAudit:
    checked_provider_count = 0
    checked_providers: list[str] = []
    graph_absent_providers: list[str] = []
    missing_typeinfos: list[str] = []
    projected_ancestor_missing_typeinfos: list[ProjectedAncestorMissing] = []
    mismatches: list[ProviderMismatch] = []
    source_modules = tuple(record.module for record in manifest.source_modules)
    for projection in manifest.projections:
        provider = projection.provider
        if not provider.startswith(CONSUMER_PROVIDER_PREFIX):
            continue
        provider_module = _source_module_for_fullname(source_modules, provider)
        if provider_module is None or provider_module not in result.graph:
            graph_absent_providers.append(provider)
            continue
        info = _typeinfo_for_fullname(result, provider, provider_module)
        if info is None:
            missing_typeinfos.append(provider)
            continue
        for ancestor in _projected_ancestors(projection):
            ancestor_module = _graph_module_for_fullname(result, ancestor)
            if ancestor_module is None:
                projected_ancestor_missing_typeinfos.append(
                    ProjectedAncestorMissing(
                        provider=provider,
                        ancestor=ancestor,
                        reason="module_absent",
                    )
                )
                continue
            if _typeinfo_for_fullname(result, ancestor, ancestor_module) is None:
                projected_ancestor_missing_typeinfos.append(
                    ProjectedAncestorMissing(
                        provider=provider,
                        ancestor=ancestor,
                        reason="typeinfo_absent",
                    )
                )
        observed_bases = tuple(base.type.fullname for base in info.bases)
        observed_mro = tuple(
            mro_info.fullname
            for mro_info in info.mro
            if mro_info.fullname != "builtins.object"
        )
        if observed_bases != projection.provider_bases:
            mismatches.append(
                ProviderMismatch(
                    provider=provider,
                    field="bases",
                    expected=projection.provider_bases,
                    observed=observed_bases,
                )
            )
        if observed_mro != projection.provider_mro:
            mismatches.append(
                ProviderMismatch(
                    provider=provider,
                    field="mro",
                    expected=projection.provider_mro,
                    observed=observed_mro,
                )
            )
        checked_provider_count += 1
        checked_providers.append(provider)

    return StructuralAudit(
        checked_provider_count=checked_provider_count,
        graph_absent_provider_count=len(graph_absent_providers),
        missing_typeinfo_count=len(missing_typeinfos),
        projected_ancestor_missing_typeinfo_count=len(
            projected_ancestor_missing_typeinfos
        ),
        mismatched_provider_count=len({mismatch.provider for mismatch in mismatches}),
        checked_providers=tuple(checked_providers),
        graph_absent_providers=tuple(graph_absent_providers),
        missing_typeinfos=tuple(missing_typeinfos),
        projected_ancestor_missing_typeinfos=tuple(projected_ancestor_missing_typeinfos),
        mismatches=tuple(mismatches),
    )


def _assert_provider_typeinfos_match_manifest(
    structural_audit: StructuralAudit,
    *,
    require_all_graph_providers: bool,
) -> None:
    if structural_audit.mismatches:
        mismatch = structural_audit.mismatches[0]
        raise AssertionError(
            f"{mismatch.provider} TypeInfo.{mismatch.field} mismatch: "
            f"expected {mismatch.expected!r}, observed {mismatch.observed!r}"
        )

    if structural_audit.checked_provider_count == 0:
        raise AssertionError("No category_specs provider TypeInfos were checked")
    if require_all_graph_providers and structural_audit.graph_absent_provider_count:
        raise AssertionError(
            "Full consumer structural canary left "
            f"{structural_audit.graph_absent_provider_count} projected "
            "category_specs providers "
            "outside the mypy graph"
        )
    if structural_audit.missing_typeinfos:
        missing = "\n  ".join(structural_audit.missing_typeinfos)
        raise AssertionError(f"Missing TypeInfo for loaded providers:\n  {missing}")
    if structural_audit.projected_ancestor_missing_typeinfos:
        missing = "\n  ".join(
            f"{entry.provider} -> {entry.ancestor} ({entry.reason})"
            for entry in structural_audit.projected_ancestor_missing_typeinfos
        )
        raise AssertionError(f"Missing projected ancestor TypeInfo:\n  {missing}")


def _write_artifacts(
    *,
    artifact_dir: Path,
    paths: CanaryPaths,
    consumer_root: Path,
    build_plan: BuildPlan,
    result: BuildResult,
    manifest: ProjectionManifest,
    structural_audit: StructuralAudit,
    generated_stub_cache_absent: bool,
    negative_error_count: int,
) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    payload = _artifact_payload(
        paths=paths,
        consumer_root=consumer_root,
        build_plan=build_plan,
        result=result,
        manifest=manifest,
        structural_audit=structural_audit,
        generated_stub_cache_absent=generated_stub_cache_absent,
        negative_error_count=negative_error_count,
    )
    (artifact_dir / "latest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifact_dir / "latest.md").write_text(
        _artifact_markdown(payload),
        encoding="utf-8",
    )


def _artifact_payload(
    *,
    paths: CanaryPaths,
    consumer_root: Path,
    build_plan: BuildPlan,
    result: BuildResult,
    manifest: ProjectionManifest,
    structural_audit: StructuralAudit,
    generated_stub_cache_absent: bool,
    negative_error_count: int,
) -> dict[str, object]:
    status = "pass"
    if (
        not generated_stub_cache_absent
        or negative_error_count == 0
        or structural_audit.checked_provider_count == 0
        or (
            build_plan.requires_all_graph_providers
            and structural_audit.graph_absent_provider_count
        )
        or structural_audit.missing_typeinfo_count
        or structural_audit.projected_ancestor_missing_typeinfo_count
        or structural_audit.mismatched_provider_count
    ):
        status = "fail"

    return {
        "status": status,
        "consumer_root": str(consumer_root),
        "work_dir": str(paths.config_path.parent),
        "manifest": str(paths.cache_dir / "projection-manifest.json"),
        "projection_trace": str(paths.projection_trace_path),
        "source_mode": build_plan.mode,
        "requires_all_graph_providers": build_plan.requires_all_graph_providers,
        "source_module_count": len(build_plan.sources),
        "manifest_source_module_count": len(manifest.source_modules),
        "projection_count": len(manifest.projections),
        "unsupported_provider_count": len(manifest.unsupported_providers),
        "generated_stub_cache_absent": generated_stub_cache_absent,
        "negative_injected_error_count": negative_error_count,
        "mypy_error_count": len(result.errors),
        "mypy_errors": result.errors,
        "checked_provider_count": structural_audit.checked_provider_count,
        "graph_absent_provider_count": structural_audit.graph_absent_provider_count,
        "missing_typeinfo_count": structural_audit.missing_typeinfo_count,
        "projected_ancestor_missing_typeinfo_count": (
            structural_audit.projected_ancestor_missing_typeinfo_count
        ),
        "mismatched_provider_count": structural_audit.mismatched_provider_count,
        "checked_providers": structural_audit.checked_providers,
        "graph_absent_providers": structural_audit.graph_absent_providers,
        "missing_typeinfos": structural_audit.missing_typeinfos,
        "projected_ancestor_missing_typeinfos": [
            {
                "provider": entry.provider,
                "ancestor": entry.ancestor,
                "reason": entry.reason,
            }
            for entry in structural_audit.projected_ancestor_missing_typeinfos
        ],
        "mismatches": [
            {
                "provider": mismatch.provider,
                "field": mismatch.field,
                "expected": mismatch.expected,
                "observed": mismatch.observed,
            }
            for mismatch in structural_audit.mismatches
        ],
        "projection_trace_events": _projection_trace_events(
            paths,
            providers=tuple(
                dict.fromkeys(mismatch.provider for mismatch in structural_audit.mismatches)
            ),
        ),
    }


def _artifact_markdown(payload: dict[str, object]) -> str:
    projection_trace_events = payload["projection_trace_events"]
    if not isinstance(projection_trace_events, list):
        raise AssertionError("projection_trace_events artifact field must be a list")
    lines = [
        "# Consumer Structural Canary",
        "",
        f"- status: {payload['status']}",
        f"- source_mode: {payload['source_mode']}",
        f"- source_module_count: {payload['source_module_count']}",
        f"- projection_count: {payload['projection_count']}",
        f"- unsupported_provider_count: {payload['unsupported_provider_count']}",
        f"- checked_provider_count: {payload['checked_provider_count']}",
        f"- graph_absent_provider_count: {payload['graph_absent_provider_count']}",
        f"- missing_typeinfo_count: {payload['missing_typeinfo_count']}",
        "- projected_ancestor_missing_typeinfo_count: "
        f"{payload['projected_ancestor_missing_typeinfo_count']}",
        f"- mismatched_provider_count: {payload['mismatched_provider_count']}",
        f"- negative_injected_error_count: {payload['negative_injected_error_count']}",
        f"- projection_trace_event_count: {len(projection_trace_events)}",
        "",
        "## Mismatches",
        "",
    ]
    mismatches = payload["mismatches"]
    if isinstance(mismatches, list) and mismatches:
        for mismatch in mismatches:
            lines.extend(
                [
                    f"### {mismatch['provider']}",
                    "",
                    f"- field: {mismatch['field']}",
                    f"- expected: `{tuple(mismatch['expected'])}`",
                    f"- observed: `{tuple(mismatch['observed'])}`",
                    "",
                ]
            )
    else:
        lines.append("None.")
        lines.append("")
    lines.extend(
        [
            "## Missing TypeInfos",
            "",
            *_markdown_items(payload["missing_typeinfos"]),
            "",
            "## Missing Projected Ancestor TypeInfos",
            "",
            *_projected_ancestor_missing_markdown_items(
                payload["projected_ancestor_missing_typeinfos"]
            ),
            "",
            "## Graph-Absent Providers",
            "",
            *_markdown_items(payload["graph_absent_providers"]),
            "",
            "## Mypy Errors",
            "",
            *_markdown_items(payload["mypy_errors"]),
            "",
            "## Projection Hook Trace",
            "",
            *_projection_trace_markdown_items(projection_trace_events),
            "",
        ]
    )
    return "\n".join(lines)


def _markdown_items(value: object) -> list[str]:
    if not isinstance(value, list | tuple) or not value:
        return ["None."]
    return [f"- `{item}`" for item in value]


def _projected_ancestor_missing_markdown_items(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["None."]
    return [
        f"- `{entry['provider']}` -> `{entry['ancestor']}` ({entry['reason']})"
        for entry in value
        if isinstance(entry, dict)
    ]


def _projected_ancestors(projection: ProviderProjection) -> tuple[str, ...]:
    ancestors = [
        ancestor
        for ancestor in (*projection.provider_bases, *projection.provider_mro)
        if ancestor != projection.provider and ancestor != "builtins.object"
    ]
    return tuple(dict.fromkeys(ancestors))


def _projection_trace_events(
    paths: CanaryPaths,
    *,
    providers: tuple[str, ...],
) -> list[dict[str, object]]:
    if not paths.projection_trace_path.is_file():
        return []
    provider_set = frozenset(providers)
    if not provider_set:
        return []
    events: list[dict[str, object]] = []
    for line in paths.projection_trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        loaded = json.loads(line)
        if not isinstance(loaded, dict):
            raise AssertionError(f"Projection trace event is not an object: {loaded!r}")
        if loaded.get("provider") not in provider_set:
            continue
        events.append(loaded)
    return events


def _projection_trace_markdown_items(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["None."]
    lines: list[str] = []
    for event in value:
        if not isinstance(event, dict):
            continue
        provider = event.get("provider")
        event_name = event.get("event")
        final_iteration = event.get("final_iteration")
        missing = event.get("missing")
        suffix = ""
        if final_iteration is not None:
            suffix += f", final_iteration={final_iteration}"
        if missing:
            suffix += f", missing={tuple(missing)}"
        lines.append(f"- `{provider}`: `{event_name}`{suffix}")
    return lines or ["None."]


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


def _graph_module_for_fullname(result: BuildResult, fullname: str) -> str | None:
    matches = [
        module
        for module in result.graph
        if fullname == module or fullname.startswith(f"{module}.")
    ]
    if not matches:
        return None
    return max(matches, key=len)


if __name__ == "__main__":
    main()
