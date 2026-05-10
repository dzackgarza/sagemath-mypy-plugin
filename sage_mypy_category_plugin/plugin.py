"""
Mypy plugin for Sage's dynamic category method system.

Injects Sage semantic bases into method container MRO so that standard
@override (typing.override) works for ParentMethods, ElementMethods,
MorphismMethods, and SubcategoryMethods.

The hook fires after calculate_mro computes MRO from info.bases. Since
@override checking walks info.mro (not info.bases), we must splice
ancestor method containers directly into info.mro between the class
itself and the final `object` entry.
"""
from __future__ import annotations
import configparser
import csv
from typing import Any, Callable, TYPE_CHECKING, Tuple
from mypy.build import PRI_MED
from mypy.errorcodes import ErrorCode
from mypy.plugin import Plugin, ClassDefContext
if TYPE_CHECKING:
    from mypy.types import Instance


SAGE_CATEGORY_UNRESOLVED = ErrorCode(
    "sage-category-unresolved",
    "Report Sage category method-container projection failures",
    "Sage",
)
SAGE_CATEGORY_PARAMETERIZED = ErrorCode(
    "sage-category-parameterized",
    "Report unresolved parameterized Sage category method containers",
    "Sage",
)
SAGE_CATEGORY_BASE_UNMAPPED = ErrorCode(
    "sage-category-base-unmapped",
    "Report dynamic Sage bases that cannot be mapped to source containers",
    "Sage",
)
SAGE_CATEGORY_TYPEINFO_MISSING = ErrorCode(
    "sage-category-typeinfo-missing",
    "Report projected Sage method containers missing from mypy's module graph",
    "Sage",
)


def plugin(version: str) -> type[Plugin]:
    return SageCategoryPlugin

class SageCategoryPlugin(Plugin):
    def __init__(self, options: Any) -> None:
        super().__init__(options)
        self._strict = False
        self._representatives: dict[str, tuple[str, ...]] = {}
        self._load_config(getattr(options, "config_file", None))

    def get_customize_class_mro_hook(self, fullname: str) -> Callable | None:
        if _fast_is_sage_container(fullname):
            return self._mro_hook
        return None

    def get_additional_deps(self, file: Any) -> list[Tuple[int, str, int]]:
        module_name = getattr(file, "fullname", None)
        if not module_name:
            return []
        try:
            from sage_mypy_category_plugin.introspection import (
                module_method_container_dependencies,
            )
            deps = module_method_container_dependencies(module_name)
        except Exception:
            return []
        return [(PRI_MED, dep, -1) for dep in deps if dep != module_name]

    def report_config_data(self, ctx: Any) -> dict[str, Any]:
        return {
            "plugin_version": "0.2.0",
            "sage_version": _sage_version(),
            "strict": self._strict,
            "configured_representatives": {
                key: list(value) for key, value in sorted(self._representatives.items())
            },
        }

    def _mro_hook(self, ctx: ClassDefContext) -> None:
        info = ctx.cls.info
        fullname = info.fullname

        projection = self._resolve_projection(ctx, fullname)
        if projection is None:
            return

        if projection.unmapped_dynamic_bases and self._strict:
            for base in projection.unmapped_dynamic_bases:
                ctx.api.fail(
                    f"Sage dynamic base has no source method container: {base}",
                    ctx.cls,
                    code=SAGE_CATEGORY_BASE_UNMAPPED,
                )

        if not projection.static_bases:
            return

        base_tis: list = []
        deferred = False
        for base_fn in projection.static_bases:
            ti = _lookup_typeinfo(ctx, base_fn)
            if ti is None:
                if self._strict and ctx.api.final_iteration:
                    ctx.api.fail(
                        f"Sage projected method-container base is not loaded by mypy: {base_fn}",
                        ctx.cls,
                        code=SAGE_CATEGORY_TYPEINFO_MISSING,
                    )
                else:
                    deferred = True
                continue
            base_tis.append(ti)

        if deferred:
            ctx.api.defer()
            return

        if not base_tis:
            return

        # Splice ancestor TypeInfos into MRO before the final 'object' entry
        head = info.mro[:-1]  # everything except object
        tail = [info.mro[-1]]  # object
        info.mro = head + base_tis + tail

    def _resolve_projection(self, ctx: ClassDefContext, fullname: str) -> Any | None:
        idx = fullname.find("sage.categories.")
        if idx > 0:
            fullname = fullname[idx:]
        try:
            from sage_mypy_category_plugin.introspection import (
                ParameterizedCategoryError,
                method_container_projection,
            )
            return method_container_projection(fullname, self._representatives)
        except ParameterizedCategoryError as exc:
            if self._strict:
                ctx.api.fail(str(exc), ctx.cls, code=SAGE_CATEGORY_PARAMETERIZED)
            return None
        except Exception as exc:
            if self._strict:
                ctx.api.fail(
                    f"Sage category method-container projection failed: {exc}",
                    ctx.cls,
                    code=SAGE_CATEGORY_UNRESOLVED,
                )
            return None

    def _load_config(self, config_file: str | None) -> None:
        if not config_file:
            return

        parser = configparser.ConfigParser()
        parser.optionxform = str
        parser.read(config_file)
        section = "sage-mypy-category-plugin"
        if not parser.has_section(section):
            return

        self._strict = parser.getboolean(section, "strict", fallback=False)
        for key, value in parser.items(section):
            if not key.startswith("representative."):
                continue
            category_fullname = key.removeprefix("representative.")
            self._representatives[category_fullname] = tuple(_parse_args(value))


_METHOD_KINDS = frozenset({
    "ParentMethods", "ElementMethods", "MorphismMethods", "SubcategoryMethods",
})

def _fast_is_sage_container(fullname: str) -> bool:
    if not any(fullname.endswith("." + k) for k in _METHOD_KINDS):
        return False
    return (
        fullname.startswith("sage.categories.")
        or ".sage.categories." in fullname
    )

def _resolve_direct_bases(fullname: str) -> list[str] | None:
    idx = fullname.find("sage.categories.")
    if idx > 0:
        fullname = fullname[idx:]
    try:
        from sage_mypy_category_plugin.introspection import (
            method_container_direct_bases,
        )
        return method_container_direct_bases(fullname)
    except Exception:
        return None


def _parse_args(value: str) -> list[str]:
    if not value.strip():
        return []
    return [item.strip() for item in next(csv.reader([value]))]


def _sage_version() -> str | None:
    try:
        from sage.version import version
        return str(version)
    except Exception:
        return None

def _lookup_typeinfo(ctx: ClassDefContext, fullname: str) -> Any | None:
    parts = fullname.split(".")
    for i in range(len(parts) - 1, -1, -1):
        candidate_mod = ".".join(parts[:i])
        rel = ".".join(parts[i:])
        if not rel:
            continue
        for mod_key, mod in ctx.api.modules.items():
            if mod_key.endswith(candidate_mod):
                if not hasattr(mod, "names"):
                    continue
                node = _walk_chain(mod, rel)
                if node is not None:
                    return node
    return None

def _walk_chain(container: Any, name_chain: str) -> Any | None:
    for p in name_chain.split("."):
        if not hasattr(container, "names"):
            return None
        st = container.names.get(p)
        if st is None or st.node is None:
            return None
        container = st.node
    if container and hasattr(container, "defn"):
        return container
    return None
