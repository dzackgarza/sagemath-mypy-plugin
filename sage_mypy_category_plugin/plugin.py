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
from typing import Any, Callable, TYPE_CHECKING, Tuple
from mypy.plugin import Plugin, ClassDefContext
if TYPE_CHECKING:
    from mypy.types import Instance

def plugin(version: str) -> type[Plugin]:
    return SageCategoryPlugin

class SageCategoryPlugin(Plugin):
    def __init__(self, options: Any) -> None:
        super().__init__(options)

    def get_customize_class_mro_hook(self, fullname: str) -> Callable | None:
        if _fast_is_sage_container(fullname):
            return self._mro_hook
        return None

    def get_additional_deps(self, file: Any) -> list[Tuple[int, str, int]]:
        return []

    def report_config_data(self, ctx: Any) -> dict[str, Any]:
        return {"plugin_version": "0.1.0"}

    def _mro_hook(self, ctx: ClassDefContext) -> None:
        info = ctx.cls.info
        fullname = info.fullname

        base_fullnames = _resolve_direct_bases(fullname)
        if not base_fullnames:
            return

        base_tis: list = []
        deferred = False
        for base_fn in base_fullnames:
            ti = _lookup_typeinfo(ctx, base_fn)
            if ti is None:
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
