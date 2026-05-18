from __future__ import annotations

from configparser import ConfigParser
from hashlib import sha256
from pathlib import Path
from typing import Callable

from mypy.errors import CompileError
from mypy.nodes import MypyFile, TypeInfo
from mypy.options import Options
from mypy.plugin import ClassDefContext, Plugin, ReportConfigContext
from mypy.types import Instance

from sage_mypy_category_plugin.manifest import ProjectionManifest, load_manifest
from sage_mypy_category_plugin.projection import ProviderProjection

CONFIG_SECTION = "sage-mypy-category-plugin"
MYPY_OBJECT = "builtins.object"
MYPY_DEP_PRIORITY = 10


class SageCategoryProjectionPlugin(Plugin):
    def __init__(self, options: Options) -> None:
        super().__init__(options)
        self._manifest_path = _manifest_path_from_config(options)
        self._manifest = load_manifest(self._manifest_path)
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


def _manifest_path_from_config(options: Options) -> Path:
    if options.config_file is None:
        raise CompileError(["mypy config file is required"])

    config_path = Path(options.config_file)
    parser = ConfigParser()
    parsed_files = parser.read(config_path)
    if parsed_files != [str(config_path)]:
        raise CompileError([f"Could not read {config_path}"])
    if not parser.has_section(CONFIG_SECTION):
        raise CompileError([f"Missing [{CONFIG_SECTION}] section in {config_path}"])
    if not parser.has_option(CONFIG_SECTION, "manifest"):
        raise CompileError(
            [f"Missing manifest option in [{CONFIG_SECTION}] section of {config_path}"]
        )

    manifest_path = Path(parser.get(CONFIG_SECTION, "manifest"))
    if not manifest_path.is_absolute():
        manifest_path = config_path.parent / manifest_path
    return manifest_path


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
]
