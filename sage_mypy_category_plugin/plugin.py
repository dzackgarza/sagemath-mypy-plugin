"""
Universal method-container override plugin for mypy.

Matches any class whose simple name is ParentMethods, ElementMethods,
MorphismMethods, or SubcategoryMethods. Resolves ancestors by walking
the enclosing class's Python MRO in mypy's module graph and collecting
any same-named container from each ancestor.

Sage introspection is used as an enhancement for Sage categories.
"""
from __future__ import annotations
from typing import Any, Callable, TYPE_CHECKING, Tuple
from mypy.plugin import Plugin, ClassDefContext

if TYPE_CHECKING:
    from mypy.types import Instance

def plugin(version: str) -> type[Plugin]:
    return ContainerOverridePlugin

class ContainerOverridePlugin(Plugin):
    def get_customize_class_mro_hook(self, fullname: str) -> Callable | None:
        if _is_method_container(fullname):
            return self._mro_hook
        return None

    def get_additional_deps(self, file: Any) -> list[Tuple[int, str, int]]:
        return []

    def report_config_data(self, ctx: Any) -> dict[str, Any]:
        return {"plugin_version": "0.4.0"}

    def _mro_hook(self, ctx: ClassDefContext) -> None:
        info = ctx.cls.info
        mc_name = info.fullname.rsplit(".", 1)[-1]

        enclosing_fn = info.fullname.rsplit(".", 1)[0]
        enclosing = _lookup_typeinfo(ctx, enclosing_fn)
        if enclosing is None:
            return

        ancestors = _resolve_ancestors(ctx, enclosing, mc_name)
        if not ancestors:
            return

        ancestor_tis = []
        deferred = False
        for afn in ancestors:
            ti = _lookup_typeinfo(ctx, afn)
            if ti is None:
                deferred = True
                continue
            ancestor_tis.append(ti)

        if deferred:
            ctx.api.defer()
            return
        if not ancestor_tis:
            return

        info.mro = info.mro[:-1] + ancestor_tis + [info.mro[-1]]


_CONTAINER_NAMES = frozenset({
    "ParentMethods", "ElementMethods", "MorphismMethods", "SubcategoryMethods",
})

def _is_method_container(fullname: str) -> bool:
    return fullname.rsplit(".", 1)[-1] in _CONTAINER_NAMES


def _resolve_ancestors(ctx, enclosing: Any, mc_name: str) -> list[str]:
    """Resolve ancestor method containers.

    Python MRO: walk enclosing's MRO, collecting same-named containers.
    Sage enhancement: if available, augment with Sage's dynamic bases.
    """
    result = []
    for ancestor in enclosing.mro[1:]:
        container_fn = ancestor.fullname + "." + mc_name
        if _lookup_typeinfo(ctx, container_fn) is not None:
            result.append(container_fn)

    # Sage enhancement for dynamic category method injection
    augmented = _sage_augment(enclosing.fullname, mc_name, result)
    return augmented or result


def _sage_augment(enclosing_fn: str, mc_name: str, existing: list[str]) -> list[str] | None:
    """Try Sage introspection to find dynamic method-container bases."""
    container_fn = enclosing_fn + "." + mc_name
    idx = container_fn.find("sage.categories.")
    if idx < 0:
        return None
    try:
        from sage_mypy_category_plugin.introspection import method_container_direct_bases
        sage_bases = method_container_direct_bases(container_fn[idx:] if idx > 0 else container_fn)
        if sage_bases:
            seen = set(existing)
            result = list(existing)
            for b in sage_bases:
                if b not in seen:
                    result.append(b)
                    seen.add(b)
            return result
    except Exception:
        pass
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
    return container if hasattr(container, "defn") else None
