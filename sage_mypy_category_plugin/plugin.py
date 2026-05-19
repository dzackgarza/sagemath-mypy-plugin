from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass, field
from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path
from site import getsitepackages, getusersitepackages
from sysconfig import get_paths
from typing import Callable, Sequence

from mypy.errors import CompileError
from mypy.nodes import MypyFile, TypeInfo
from mypy.options import Options
from mypy.plugin import ClassDefContext, Plugin, ReportConfigContext
from mypy.types import Instance
from pydantic import ValidationError

from sage_mypy_category_plugin.manifest import (
    ProjectionManifest,
    SourceModuleRecord,
    load_manifest,
    write_manifest,
)
from sage_mypy_category_plugin.projection import ProviderProjection, ProviderRole

CONFIG_SECTION = "sage-mypy-category-plugin"
MYPY_OBJECT = "builtins.object"
MYPY_DEP_PRIORITY = 10

DEFAULT_CACHE_DIR = ".mypy_cache/sage-category-plugin"
DEFAULT_ROLES: tuple[ProviderRole, ...] = ("parent",)


@dataclass(frozen=True)
class PluginConfig:
    packages: tuple[str, ...] = ()
    roles: tuple[ProviderRole, ...] = DEFAULT_ROLES
    cache_dir: Path | None = None
    strict: bool = False
    debug_manifest: Path | None = None


class SageCategoryProjectionPlugin(Plugin):
    def __init__(self, options: Options) -> None:
        super().__init__(options)
        config = _read_plugin_config(options)

        if config.debug_manifest is not None:
            self._manifest = _load_manifest_for_plugin(config.debug_manifest)
            self._manifest_path = config.debug_manifest
            if self._manifest.source_modules:
                _generate_and_write_stubs(
                    self._manifest,
                    manifest_path=self._manifest_path,
                    stub_root=_stub_root_for_manifest(self._manifest_path),
                )
                _add_generated_stubs_to_mypy_path(
                    options,
                    stub_root=_stub_root_for_manifest(self._manifest_path),
                )
                self._manifest = load_manifest(self._manifest_path)
        else:
            self._manifest, self._manifest_path = _generate_and_cache(config)
            _add_generated_stubs_to_mypy_path(
                options, stub_root=_stub_root_for_manifest(self._manifest_path)
            )
            self._manifest = load_manifest(self._manifest_path)

        _validate_source_module_metadata(self._manifest.source_modules)
        self._manifest_digest = sha256(self._manifest_path.read_bytes()).hexdigest()
        self._projection_by_provider = self._manifest.projection_by_provider
        self._source_modules = tuple(
            record.module for record in self._manifest.source_modules
        )

    def get_customize_class_mro_hook(
        self,
        fullname: str,
    ) -> Callable[[ClassDefContext], None] | None:
        if fullname not in self._projection_by_provider:
            return None
        return self._customize_provider_mro

    def get_additional_deps(self, file: MypyFile) -> list[tuple[int, str, int]]:
        provider_module = file.fullname
        dependent_modules = {
            _provider_module(
                base_fullname,
                source_modules=self._source_modules,
            )
            for projection in self._manifest.projections
            if _provider_module(
                projection.provider,
                source_modules=self._source_modules,
            )
            == provider_module
            for base_fullname in (
                *projection.provider_bases,
                *projection.provider_mro,
            )
            if _provider_module(
                base_fullname,
                source_modules=self._source_modules,
            )
            != provider_module
        }
        return [
            (MYPY_DEP_PRIORITY, module_name, -1)
            for module_name in sorted(dependent_modules)
        ]

    def report_config_data(self, ctx: ReportConfigContext) -> dict[str, str]:
        return {
            "manifest_path": str(self._manifest_path),
            "manifest_digest": self._manifest_digest,
            "manifest_semantic_projection_digest": (
                self._manifest.semantic_projection_digest
            ),
            "manifest_plugin_schema_version": self._manifest.plugin_schema_version,
            "manifest_sage_version": self._manifest.sage_version,
            "manifest_sage_git_revision": self._manifest.sage_git_revision or "",
            "manifest_mypy_min_version": self._manifest.mypy_min_version,
            "manifest_mypy_max_version": self._manifest.mypy_max_version,
            "manifest_source_module_digest": self._manifest.source_module_digest,
        }

    def _customize_provider_mro(self, ctx: ClassDefContext) -> None:
        info = ctx.cls.info
        projection = self._projection_by_provider[info.fullname]
        base_infos = _lookup_provider_bases(ctx, projection)
        if base_infos is None:
            return

        mro_infos = _lookup_provider_mro(ctx, projection)
        object_info = _lookup_typeinfo(ctx, MYPY_OBJECT)
        if mro_infos is None or object_info is None:
            return

        info.bases = [Instance(base_info, []) for base_info in base_infos]
        info.mro = [*mro_infos, object_info]

        observed_provider_mro = tuple(
            mro_info.fullname
            for mro_info in info.mro
            if mro_info.fullname != MYPY_OBJECT
        )
        if observed_provider_mro != projection.provider_mro:
            ctx.api.fail(
                "Sage category provider MRO mismatch: "
                f"expected {projection.provider_mro!r}, "
                f"observed {observed_provider_mro!r}",
                ctx.cls,
            )


def _lookup_provider_bases(
    ctx: ClassDefContext,
    projection: ProviderProjection,
) -> tuple[TypeInfo, ...] | None:
    return _lookup_typeinfos(
        ctx=ctx,
        fullnames=projection.provider_bases,
        projection_field="provider_bases",
        projection_fullname=projection.provider,
    )


def _lookup_provider_mro(
    ctx: ClassDefContext,
    projection: ProviderProjection,
) -> tuple[TypeInfo, ...] | None:
    return _lookup_typeinfos(
        ctx=ctx,
        fullnames=projection.provider_mro,
        projection_field="provider_mro",
        projection_fullname=projection.provider,
    )


def _lookup_typeinfos(
    ctx: ClassDefContext,
    *,
    projection_field: str,
    projection_fullname: str,
    fullnames: tuple[str, ...],
) -> tuple[TypeInfo, ...] | None:
    typeinfos: list[TypeInfo] = []
    missing_names: list[str] = []
    for fullname in fullnames:
        typeinfo = _lookup_typeinfo(ctx, fullname, report_missing=False)
        if typeinfo is None:
            missing_names.append(fullname)
            continue
        typeinfos.append(typeinfo)

    if missing_names:
        ctx.api.fail(
            "Sage category provider projection for "
            f"{projection_fullname!r} cannot be applied because {projection_field} "
            f"references missing symbols: {', '.join(missing_names)}",
            ctx.cls,
        )
        return None

    return tuple(typeinfos)


def _lookup_typeinfo(
    ctx: ClassDefContext,
    fullname: str,
    *,
    report_missing: bool = True,
) -> TypeInfo | None:
    symbol = ctx.api.lookup_fully_qualified_or_none(fullname)
    if symbol is None or not isinstance(symbol.node, TypeInfo):
        if report_missing:
            ctx.api.fail(f"Sage category TypeInfo is missing: {fullname}", ctx.cls)
        return None
    return symbol.node


# ── Config parsing ───────────────────────────────────────────────────────────


def _read_plugin_config(options: Options) -> PluginConfig:
    if options.config_file is None:
        raise CompileError(["mypy config file is required"])

    config_path = Path(options.config_file)
    parser = ConfigParser()
    parsed_files = parser.read(config_path)
    if parsed_files != [str(config_path)]:
        raise CompileError([f"Could not read {config_path}"])

    if not parser.has_section(CONFIG_SECTION):
        raise CompileError([f"Missing [{CONFIG_SECTION}] section in {config_path}"])

    has_manifest = parser.has_option(CONFIG_SECTION, "manifest")
    has_packages = parser.has_option(CONFIG_SECTION, "packages")

    if not has_manifest and not has_packages:
        raise CompileError(
            [
                f"[{CONFIG_SECTION}] section in {config_path} must specify either "
                "'manifest' (debug/pregenerated path) or 'packages' (auto-generation)"
            ]
        )

    packages: tuple[str, ...] = ()
    if has_packages:
        packages = _parse_multiline_option(parser, CONFIG_SECTION, "packages")

    roles: tuple[ProviderRole, ...] = DEFAULT_ROLES
    if parser.has_option(CONFIG_SECTION, "roles"):
        raw_roles = _parse_multiline_option(parser, CONFIG_SECTION, "roles")
        roles = _parse_roles(config_path, raw_roles)

    cache_dir: Path | None = None
    if parser.has_option(CONFIG_SECTION, "cache_dir"):
        raw_cache_dir = parser.get(CONFIG_SECTION, "cache_dir")
        cache_dir = Path(raw_cache_dir)
        if not cache_dir.is_absolute():
            cache_dir = config_path.parent / cache_dir

    strict: bool = False
    if parser.has_option(CONFIG_SECTION, "strict"):
        strict = parser.getboolean(CONFIG_SECTION, "strict")

    debug_manifest: Path | None = None
    if has_manifest:
        raw_path = parser.get(CONFIG_SECTION, "manifest")
        debug_manifest = Path(raw_path)
        if not debug_manifest.is_absolute():
            debug_manifest = config_path.parent / debug_manifest

    return PluginConfig(
        packages=packages,
        roles=roles,
        cache_dir=cache_dir,
        strict=strict,
        debug_manifest=debug_manifest,
    )


def _parse_multiline_option(
    parser: ConfigParser,
    section: str,
    option: str,
) -> tuple[str, ...]:
    raw = parser.get(section, option)
    return tuple(
        item.strip()
        for line in raw.splitlines()
        for item in (line.split("#")[0].strip(),)
        if item
    )


def _parse_roles(
    config_path: Path,
    raw_roles: tuple[str, ...],
) -> tuple[ProviderRole, ...]:
    from typing import get_args

    valid_roles: tuple[ProviderRole, ...] = get_args(ProviderRole)
    roles: list[ProviderRole] = []
    for raw in raw_roles:
        # Map user-friendly names to ProviderRole literals
        role = _normalize_role_name(raw)
        if role not in valid_roles:
            raise CompileError(
                [
                    f"Invalid role {raw!r} in [{CONFIG_SECTION}] section of "
                    f"{config_path}. Valid roles: {', '.join(valid_roles)}"
                ]
            )
        roles.append(role)
    return tuple(dict.fromkeys(roles))


def _normalize_role_name(raw: str) -> str:
    """Map common role name variants to ProviderRole literals."""
    normalized = raw.strip().lower()
    # Handle combined names like "homset_parent" -> "homset_parent", "homset parent" -> "homset_parent"
    role_map = {
        "parent": "parent",
        "element": "element",
        "subcategory": "subcategory",
        "morphism": "morphism",
        "homset_parent": "homset_parent",
        "homset parent": "homset_parent",
        "homsetparent": "homset_parent",
        "homset_element": "homset_element",
        "homset element": "homset_element",
        "homsetelement": "homset_element",
    }
    return role_map.get(normalized, normalized)


# ── Manifest generation ──────────────────────────────────────────────────────


def _generate_and_cache(config: PluginConfig) -> tuple[ProjectionManifest, Path]:
    from sage_mypy_category_plugin.resolver import (
        discover_category_fullnames,
        resolve_projection_manifest,
    )
    from sage_mypy_category_plugin.stubs import write_generated_stub_tree

    category_fullnames = discover_category_fullnames(config.packages)
    if not category_fullnames:
        raise CompileError(
            [
                f"No Sage category classes found in configured packages: "
                f"{', '.join(config.packages)}"
            ]
        )

    manifest = resolve_projection_manifest(
        category_fullnames=category_fullnames,
        roles=config.roles,
    )

    # Generate stubs into manifest-relative directory
    cache_dir = _resolve_cache_dir(config)
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / "projection-manifest.json"
    stub_root = _stub_root_for_manifest(manifest_path)

    stub_source_modules = write_generated_stub_tree(
        stub_root,
        manifest,
        preserved_source_module_prefixes=_preserved_source_module_prefixes(
            manifest,
            manifest_path=manifest_path,
        ),
    )

    # Update manifest with stub-augmented source modules
    manifest = manifest.model_copy(
        update={"source_modules": stub_source_modules}
    )
    write_manifest(manifest_path, manifest)

    return manifest, manifest_path


def _add_generated_stubs_to_mypy_path(options: Options, *, stub_root: Path) -> None:
    """Ensure mypy can see generated stubs without requiring MYPYPATH.

    Mutates options.mypy_path in-place during plugin initialization so callers
    that reuse Options see the generated stub root. CLI runs must also declare
    the stub root in config before mypy starts, since mypy computes import
    search paths before constructing plugins.
    """
    stub_root_str = str(stub_root.resolve())
    if options.mypy_path is None:
        options.mypy_path = []
    else:
        options.mypy_path = [
            existing_path
            for existing_path in options.mypy_path
            if existing_path != stub_root_str
        ]
    options.mypy_path.insert(0, stub_root_str)


def _generate_and_write_stubs(
    manifest: ProjectionManifest,
    *,
    manifest_path: Path,
    stub_root: Path,
) -> None:
    """Generate stubs and update the manifest on disk. Used for debug manifest path."""
    from sage_mypy_category_plugin.stubs import write_generated_stub_tree

    stub_root.mkdir(parents=True, exist_ok=True)
    stub_source_modules = write_generated_stub_tree(
        stub_root,
        manifest,
        preserved_source_module_prefixes=_preserved_source_module_prefixes(
            manifest,
            manifest_path=manifest_path,
        ),
    )
    updated = manifest.model_copy(update={"source_modules": stub_source_modules})
    write_manifest(manifest_path, updated)


def _resolve_cache_dir(config: PluginConfig) -> Path:
    if config.cache_dir is not None:
        return config.cache_dir
    return Path(DEFAULT_CACHE_DIR)


def _stub_root_for_manifest(manifest_path: Path) -> Path:
    return manifest_path.parent / "stubs"


def _preserved_source_module_prefixes(
    manifest: ProjectionManifest,
    *,
    manifest_path: Path,
) -> tuple[str, ...]:
    preserved: dict[str, None] = {}
    for record in manifest.source_modules:
        record_path = Path(record.path).resolve()
        try:
            spec = find_spec(record.module)
        except ModuleNotFoundError:
            continue
        if spec is None or spec.origin is None:
            continue
        spec_path = Path(spec.origin).resolve()
        if spec_path != record_path:
            continue
        if spec_path.suffix not in {".py", ".pyi", ".so"}:
            continue
        if _is_site_package_path(spec_path):
            continue
        preserved[record.module] = None
    return tuple(preserved)


def _is_site_package_path(path: Path) -> bool:
    resolved = path.resolve()
    for root in _site_package_roots():
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        return True
    return False


def _site_package_roots() -> tuple[Path, ...]:
    candidates = (
        *getsitepackages(),
        getusersitepackages(),
        get_paths().get("purelib", ""),
        get_paths().get("platlib", ""),
    )
    roots: list[Path] = []
    for candidate in candidates:
        if not candidate:
            continue
        root = Path(candidate).resolve()
        if root not in roots:
            roots.append(root)
    return tuple(roots)


def _load_manifest_for_plugin(path: Path) -> ProjectionManifest:
    try:
        return load_manifest(path)
    except FileNotFoundError as error:
        raise CompileError(
            [
                f"Could not read Sage category projection manifest {path}: "
                "file is missing"
            ]
        ) from error
    except ValidationError as error:
        raise CompileError(
            [
                f"Invalid Sage category projection manifest {path}: "
                f"{_format_validation_error(error)}"
            ]
        ) from error


def _format_validation_error(error: ValidationError) -> str:
    messages: list[str] = []
    for issue in error.errors():
        location = ".".join(str(part) for part in issue["loc"])
        if not location:
            location = "<manifest>"
        messages.append(f"{location}: {issue['msg']}")
    return "; ".join(messages)


def _validate_source_module_metadata(
    source_modules: tuple[SourceModuleRecord, ...],
) -> None:
    for record in source_modules:
        path = Path(record.path)
        if not path.is_file():
            raise CompileError(
                [
                    "Stale Sage category source module metadata for "
                    f"{record.module}: file is missing"
                ]
            )
        if sha256(path.read_bytes()).hexdigest() != record.sha256:
            raise CompileError(
                [
                    "Stale Sage category source module metadata for "
                    f"{record.module}: sha256 mismatch"
                ]
            )
        if path.stat().st_mtime_ns != record.mtime_ns:
            raise CompileError(
                [
                    "Stale Sage category source module metadata for "
                    f"{record.module}: mtime_ns mismatch"
                ]
            )


def _provider_module(
    provider_fullname: str,
    *,
    source_modules: tuple[str, ...] = (),
) -> str:
    source_module = _source_module_for_fullname(
        provider_fullname,
        source_modules=source_modules,
    )
    if source_module is not None:
        return source_module

    module_name, separator, _ = provider_fullname.rpartition(".")
    if separator != ".":
        raise ValueError(f"Expected provider fullname, got {provider_fullname!r}")
    module_name, separator, _ = module_name.rpartition(".")
    if separator != ".":
        raise ValueError(f"Expected nested provider fullname, got {provider_fullname!r}")
    return module_name


def _source_module_for_fullname(
    fullname: str,
    *,
    source_modules: tuple[str, ...],
) -> str | None:
    matching_modules = tuple(
        module for module in source_modules if fullname.startswith(f"{module}.")
    )
    if not matching_modules:
        return None
    return max(matching_modules, key=len)


def plugin(version: str) -> type[Plugin]:
    return SageCategoryProjectionPlugin


__all__ = [
    "SageCategoryProjectionPlugin",
    "plugin",
    "CONFIG_SECTION",
]
