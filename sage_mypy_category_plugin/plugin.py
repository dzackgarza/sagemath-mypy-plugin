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
import logging
from typing import Any, Callable, Tuple
from mypy.build import PRI_MED
from mypy.errorcodes import ErrorCode
from mypy.mro import calculate_mro
from mypy.nodes import (
    ARG_POS,
    ARG_OPT,
    ARG_NAMED_OPT,
    AssignmentStmt,
    Block,
    CallExpr,
    ClassDef,
    Decorator,
    IS_ABSTRACT,
    IfStmt,
    MDEF,
    MemberExpr,
    NameExpr,
    RefExpr,
    ReturnStmt,
    SymbolTableNode,
    TypeAlias,
    TypeInfo,
    FuncDef,
    OverloadedFuncDef,
    Var,
)
from mypy.plugin import Plugin, ClassDefContext
from mypy.types import (
    AnyType,
    CallableType,
    Instance,
    Overloaded,
    Parameters,
    TypeOfAny,
    TypeType,
    UnboundType,
    get_proper_type,
)
from mypy.typevars import fill_typevars


_LOG = logging.getLogger(__name__)

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
        if _looks_like_method_container(fullname):
            return self._mro_hook
        return None

    def get_base_class_hook(self, fullname: str) -> Callable | None:
        # Fire broadly; the hook body validates Sage category assignments and
        # method-container bindings without namespace-string filters.
        return self._category_base_hook

    def get_function_hook(self, fullname: str) -> Callable | None:
        if fullname in {
            "typing.final",
            "typing.override",
            "typing_extensions.final",
            "typing_extensions.override",
        }:
            return self._decorator_typecheck_hook
        return None

    def get_function_signature_hook(self, fullname: str) -> Callable | None:
        short = fullname.rsplit(".", 1)[-1]
        if short == "Constructors":
            return self._constructors_signature_hook
        if _could_be_sage_category_constructor_name(short):
            return lambda ctx: self._category_constructor_signature_hook(ctx, fullname)
        return None

    def get_type_analyze_hook(self, fullname: str) -> Callable | None:
        if fullname.rsplit(".", 1)[-1] in _METHOD_KINDS:
            return lambda ctx: self._method_container_alias_type_analyze_hook(ctx, fullname)
        return None

    def get_method_signature_hook(self, fullname: str) -> Callable | None:
        if fullname.rsplit(".", 1)[-1] == "Constructors":
            return self._constructors_signature_hook
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
            _LOG.debug(
                "Sage category dependency discovery failed for %s",
                module_name,
                exc_info=True,
            )
            return []
        return [(PRI_MED, dep, -1) for dep in deps if dep != module_name]

    def report_config_data(self, ctx: Any) -> dict[str, Any]:
        return {
            "plugin_version": "0.3.0",
            "sage_version": _sage_version(),
            "strict": self._strict,
            "configured_representatives": {
                key: list(value) for key, value in sorted(self._representatives.items())
            },
        }

    def _mro_hook(self, ctx: ClassDefContext) -> None:
        info = ctx.cls.info
        fullname = info.fullname
        module = ctx.api.modules.get(info.module_name)
        _recover_method_helper_bindings(ctx.api, module, info, materialize=False)
        if _has_receiver_self_methods(ctx, info) and not ctx.api.final_iteration:
            ctx.api.defer()
            return
        _materialize_receiver_self_methods(ctx, info)
        _materialize_subcategory_helpers(ctx, info)
        _materialize_operator_helpers(ctx, info)
        if _has_explicit_non_object_base(info):
            return

        projection = self._resolve_projection(ctx, fullname)
        if projection is None:
            value_dependent_bases = _completion_self_return_base_tis(ctx, ctx.cls, info)
            if value_dependent_bases:
                base_tis = value_dependent_bases
            elif (
                _has_completion_self_return(ctx.cls, info)
                and not ctx.api.final_iteration
            ):
                ctx.api.defer()
                return
            elif ctx.api.final_iteration:
                _inject_postbind_helper_bases(ctx, info, fullname)
            elif module is not None and _class_is_postbind_helper(module, fullname):
                ctx.api.defer()
            else:
                return
        else:
            value_dependent_bases = _completion_self_return_base_tis(ctx, ctx.cls, info)

        if projection is not None and projection.unmapped_dynamic_bases and self._strict:
            for base in projection.unmapped_dynamic_bases:
                ctx.api.fail(
                    f"Sage dynamic base has no source method container: {base}",
                    ctx.cls,
                    code=SAGE_CATEGORY_BASE_UNMAPPED,
                )

        if projection is not None and not projection.static_bases:
            enclosing_cat = _lookup_enclosing_category_typeinfo(ctx, info)
            if enclosing_cat is not None:
                fallback_bases = _resolve_python_category_method_container_bases(
                    ctx, enclosing_cat, info.name
                )
            else:
                fallback_bases = ()
            if not fallback_bases and not value_dependent_bases:
                if (
                    _has_completion_self_return(ctx.cls, info)
                    and not ctx.api.final_iteration
                ):
                    ctx.api.defer()
                    return
                return
            # Override projection with Python-MRO-resolved bases.
            projection = _projection_with_static_bases(projection, fallback_bases)

        base_tis: list = list(value_dependent_bases)
        deferred = False
        for base_fn in (projection.static_bases if projection is not None else ()):
            ti = _lookup_typeinfo(ctx, base_fn)
            if ti is None:
                if ctx.api.final_iteration:
                    if self._strict:
                        ctx.api.fail(
                            f"Sage projected method-container base is not loaded by mypy: {base_fn}",
                            ctx.cls,
                            code=SAGE_CATEGORY_TYPEINFO_MISSING,
                        )
                else:
                    deferred = True
                continue
            _recover_method_helper_bindings(
                ctx.api,
                ctx.api.modules.get(ti.module_name),
                ti,
                materialize=True,
            )
            if (
                self._ensure_projected_base_mro(ctx, ti, {info.fullname})
                and not ctx.api.final_iteration
            ):
                deferred = True
            base_tis.append(ti)

        if deferred:
            ctx.api.defer()
            return

        sibling_alias_base = _lookup_sibling_alias_base(ctx, info)
        if sibling_alias_base is not None:
            _recover_method_helper_bindings(
                ctx.api,
                ctx.api.modules.get(sibling_alias_base.module_name),
                sibling_alias_base,
                materialize=True,
            )
            base_tis = [sibling_alias_base]

        base_tis = [
            ti for ti in base_tis
            if ti.fullname != info.fullname
            and info not in getattr(ti, "mro", [])[1:]
        ]

        if not base_tis:
            return

        retained_bases = [
            base for base in info.bases if base.type.fullname != "builtins.object"
        ]
        base_tis = _prune_redundant_projected_bases(base_tis, retained_bases)
        existing_bases = {base.type.fullname for base in retained_bases}
        for ti in base_tis:
            if ti.fullname in existing_bases:
                continue
            retained_bases.append(fill_typevars(ti))
            existing_bases.add(ti.fullname)

        info.bases = retained_bases
        info.mro = []
        calculate_mro(info)

    def _ensure_projected_base_mro(
        self,
        ctx: ClassDefContext,
        info: TypeInfo,
        seen: set[str],
    ) -> bool:
        if info.fullname in seen:
            return False
        seen.add(info.fullname)
        if _has_explicit_non_object_base(info):
            return False

        projection = self._resolve_projection(ctx, info.fullname)
        if projection is None or not projection.static_bases:
            return False

        retained_bases = [
            base for base in info.bases if base.type.fullname != "builtins.object"
        ]
        base_tis: list[TypeInfo] = []
        deferred = False
        for base_fn in projection.static_bases:
            ti = _lookup_typeinfo(ctx, base_fn)
            if ti is None:
                if not ctx.api.final_iteration:
                    deferred = True
                continue
            _recover_method_helper_bindings(
                ctx.api,
                ctx.api.modules.get(ti.module_name),
                ti,
                materialize=True,
            )
            if self._ensure_projected_base_mro(ctx, ti, seen):
                deferred = True
            base_tis.append(ti)

        if deferred:
            return True

        base_tis = [
            ti for ti in base_tis
            if ti.fullname != info.fullname
            and info not in getattr(ti, "mro", [])[1:]
        ]
        base_tis = _prune_redundant_projected_bases(base_tis, retained_bases)
        existing_bases = {base.type.fullname for base in retained_bases}
        for ti in base_tis:
            if ti.fullname in existing_bases:
                continue
            retained_bases.append(fill_typevars(ti))
            existing_bases.add(ti.fullname)

        if not retained_bases:
            return False
        info.bases = retained_bases
        info.mro = []
        calculate_mro(info)
        return False

    def _category_base_hook(self, ctx: ClassDefContext) -> None:
        info = ctx.cls.info
        module = ctx.api.modules.get(info.module_name)
        if module is None:
            return
        _materialize_construction_selector_methods(ctx, info)
        _inject_class_body_method_container_bases(ctx, info, module)

    def _resolve_projection(self, ctx: ClassDefContext, fullname: str) -> Any | None:
        try:
            from sage_mypy_category_plugin.introspection import (
                ParameterizedCategoryError,
                method_container_projection,
                method_container_projection_for_aliases,
            )
            projection = method_container_projection(fullname, self._representatives)
            if projection is not None:
                return projection
            module = ctx.api.modules.get(ctx.cls.info.module_name)
            aliases = _resolve_method_container_aliases_from_mypy(module, fullname)
            if aliases:
                return method_container_projection_for_aliases(
                    fullname,
                    aliases,
                    self._representatives,
                )
            return None
        except ParameterizedCategoryError as exc:
            _LOG.debug(
                "Sage category method-container projection is parameterized for %s",
                fullname,
                exc_info=True,
            )
            if self._strict:
                ctx.api.fail(str(exc), ctx.cls, code=SAGE_CATEGORY_PARAMETERIZED)
            return None
        except Exception as exc:
            _LOG.debug(
                "Sage category method-container projection failed for %s",
                fullname,
                exc_info=True,
            )
            if self._strict:
                ctx.api.fail(
                    f"Sage category method-container projection failed: {exc}",
                    ctx.cls,
                    code=SAGE_CATEGORY_UNRESOLVED,
                )
            return None

    def _decorator_typecheck_hook(self, ctx: Any) -> Any:
        module = getattr(ctx.api, "tree", None)
        if module is not None:
            bindings = _method_container_symbol_bindings(module)
            _filter_postbind_method_assign_errors(ctx.api.errors, module, bindings)
        return ctx.default_return_type

    def _constructors_signature_hook(self, ctx: Any) -> Any:
        module = getattr(ctx.api, "tree", None)
        if module is not None:
            _filter_constructors_no_redef_errors(ctx.api.errors, module)
        return _sage_constructor_signature(ctx.default_signature, ctx.api)

    def _category_constructor_signature_hook(self, ctx: Any, fullname: str) -> Any:
        if not _is_mypy_sage_category_fullname(ctx.api, fullname):
            return ctx.default_signature
        return _sage_constructor_signature(ctx.default_signature, ctx.api)

    def _method_container_alias_type_analyze_hook(self, ctx: Any, fullname: str) -> Any:
        provider = _method_container_alias_provider_typeinfo(ctx.api, fullname)
        if provider is None:
            provider_fullname = _method_container_alias_provider_fullname(
                ctx.api,
                fullname,
            )
            if provider_fullname is None and not self._strict:
                return ctx.api.named_type("builtins.object", [])
            if self._strict:
                target = provider_fullname or fullname
                ctx.api.fail(
                    f"Sage method-container alias has no loaded class provider: {target}",
                    ctx.context,
                    code=SAGE_CATEGORY_TYPEINFO_MISSING,
                )
                return AnyType(TypeOfAny.from_error)
            return AnyType(TypeOfAny.special_form)
        return _instance_for_typeinfo(provider)

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

_RECEIVER_SELF_METHODS = frozenset({
    "base_category",
    "base_ring",
    "category",
})

_SAGE_CATEGORY_BASE_FULLNAMES = frozenset({
    "sage.categories.category.Category",
    "sage.categories.category_singleton.Category_singleton",
    "sage.categories.category_with_axiom.CategoryWithAxiom",
})


def _is_sage_category_typeinfo(info: TypeInfo) -> bool:
    """Return True iff *info* is a Sage Category subclass."""
    return any(
        ti.fullname in _SAGE_CATEGORY_BASE_FULLNAMES
        for ti in getattr(info, "mro", [])
    )


def _looks_like_method_container(fullname: str) -> bool:
    return fullname.rsplit(".", 1)[-1].endswith("Methods")


def _has_explicit_non_object_base(info: TypeInfo) -> bool:
    return any(base.type.fullname != "builtins.object" for base in info.bases)


def _is_mypy_sage_category_fullname(api: Any, fullname: str) -> bool:
    parts = fullname.split(".")
    for index in range(len(parts) - 1, 0, -1):
        module_name = ".".join(parts[:index])
        relative_name = ".".join(parts[index:])
        for module_key, module in getattr(api, "modules", {}).items():
            if not (
                module_key.endswith(module_name)
                or module_name.endswith(module_key)
            ):
                continue
            node = _walk_chain(module, relative_name)
            info = _typeinfo_from_symbol_node(node)
            if info is not None:
                return _looks_like_sage_category_typeinfo(info)
    try:
        from sage_mypy_category_plugin.introspection import is_sage_category_fullname

        parts = fullname.split(".")
        return any(
            is_sage_category_fullname(".".join(parts[index:]))
            for index in range(len(parts))
        )
    except Exception:
        return False


def _could_be_sage_category_constructor_name(short_name: str) -> bool:
    name = short_name.lstrip("_")
    return bool(name) and name[0].isupper()


def _looks_like_sage_category_typeinfo(info: TypeInfo) -> bool:
    if _is_sage_category_typeinfo(info):
        return True
    if any(name in info.names for name in _METHOD_KINDS):
        return True
    return "super_categories" in info.names


def _sage_constructor_signature(signature: CallableType, api: Any) -> CallableType:
    arg_types = list(signature.arg_types)
    arg_kinds = list(signature.arg_kinds)
    arg_names = list(signature.arg_names)
    changed = False

    for index, name in enumerate(arg_names):
        if name in {"base_category", "category"} and arg_kinds[index] == ARG_POS:
            arg_kinds[index] = ARG_OPT
            changed = True

    if "dispatch" not in arg_names:
        arg_types.append(api.named_type("builtins.bool"))
        arg_kinds.append(ARG_NAMED_OPT)
        arg_names.append("dispatch")
        changed = True

    if not changed:
        return signature
    return signature.copy_modified(
        arg_types=arg_types,
        arg_kinds=arg_kinds,
        arg_names=arg_names,
    )


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


def _resolve_python_category_method_container_bases(
    ctx: ClassDefContext,
    enclosing_cat: TypeInfo,
    method_kind: str,
) -> tuple[str, ...]:
    """Walk enclosing_cat's Python MRO to find sibling ParentMethods TypeInfos."""
    bases: list[str] = []
    for base in getattr(enclosing_cat, "mro", [])[1:]:
        if base.fullname == "builtins.object":
            break
        container_fn = f"{base.fullname}.{method_kind}"
        ti = _lookup_typeinfo(ctx, container_fn)
        if ti is not None:
            bases.append(ti.fullname)
    return tuple(dict.fromkeys(bases))


def _projection_with_static_bases(projection: Any, static_bases: tuple[str, ...]) -> Any:
    """Return a shallow copy of *projection* with *static_bases* replaced."""
    from dataclasses import replace
    return replace(projection, static_bases=static_bases)


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


def _prune_redundant_projected_bases(
    base_tis: list[TypeInfo],
    retained_bases: list[Instance],
) -> list[TypeInfo]:
    retained_ancestors = {
        ancestor.fullname
        for base in retained_bases
        for ancestor in getattr(base.type, "mro", [])[1:]
    }
    pruned = []
    for ti in base_tis:
        if ti.fullname in retained_ancestors:
            continue
        if any(ti in getattr(other, "mro", [])[1:] for other in base_tis):
            continue
        pruned.append(ti)
    return pruned


def _lookup_sibling_alias_base(ctx: ClassDefContext, info: TypeInfo) -> TypeInfo | None:
    short_name = info.name
    if not _looks_like_method_container(short_name) or "Sub" not in short_name:
        return None
    module = ctx.api.modules.get(info.module_name)
    names = getattr(module, "names", None)
    if names is None:
        return None
    for candidate_name in _base_alias_candidate_names(short_name):
        symbol = names.get(candidate_name)
        if symbol is None:
            continue
        candidate = _typeinfo_from_symbol_node(symbol.node)
        if candidate is not None:
            return candidate
    return None


def _base_alias_candidate_names(short_name: str) -> tuple[str, ...]:
    candidates: list[str] = []
    first = short_name.replace("Sub", "Base", 1)
    if first != short_name:
        candidates.append(first)
    all_replaced = short_name.replace("Sub", "Base")
    if all_replaced != short_name:
        candidates.append(all_replaced)
    return tuple(dict.fromkeys(candidates))


def _has_receiver_self_methods(ctx: ClassDefContext, info: TypeInfo) -> bool:
    target = _receiver_self_target(ctx, info)
    if target is None:
        return False
    owner = target
    for name in _RECEIVER_SELF_METHODS:
        if name not in info.names and not _class_body_defines(ctx.cls, name):
            if _receiver_method_type(ctx, owner, name) is not None:
                return True
    return False


def _materialize_receiver_self_methods(ctx: ClassDefContext, info: TypeInfo) -> None:
    """Expose selected category receiver methods on method-container ``self``."""
    target = _receiver_self_target(ctx, info)
    if target is None:
        return
    owner = target
    for name in _RECEIVER_SELF_METHODS:
        if name in info.names or _class_body_defines(ctx.cls, name):
            continue
        method_type = _receiver_method_type(ctx, owner, name)
        if method_type is None:
            continue
        var = Var(name, method_type)
        var.info = info
        var._fullname = f"{info.fullname}.{name}"
        info.names[name] = SymbolTableNode(MDEF, var, plugin_generated=True)


def _receiver_self_target(
    ctx: ClassDefContext,
    info: TypeInfo,
) -> TypeInfo | None:
    if info.name in {"ParentMethods", "ElementMethods", "SubcategoryMethods"}:
        owner = _lookup_enclosing_category_typeinfo(ctx, info)
        if owner is not None:
            return owner
    return _lookup_alias_receiver_self_target(ctx, info)


def _lookup_alias_receiver_self_target(
    ctx: ClassDefContext,
    info: TypeInfo,
) -> TypeInfo | None:
    module = ctx.api.modules.get(info.module_name)
    if module is None:
        return None
    helper_name = info.name
    module_fullname = getattr(module, "fullname", "")
    for owner_def in _module_statements(module):
        if not isinstance(owner_def, ClassDef):
            continue
        for statement in owner_def.defs.body:
            if not isinstance(statement, AssignmentStmt) or len(statement.lvalues) != 1:
                continue
            target = statement.lvalues[0]
            if not isinstance(target, NameExpr) or target.name not in _METHOD_KINDS:
                continue
            if _assigned_method_container_name(statement.rvalue) != helper_name:
                continue
            owner = _lookup_typeinfo(ctx, _fullname_for_class(module_fullname, owner_def))
            if owner is not None:
                return owner
    return None


def _receiver_method_type(
    ctx: ClassDefContext,
    owner: TypeInfo,
    name: str,
) -> CallableType | None:
    for base in getattr(owner, "mro", []):
        symbol = base.names.get(name)
        if symbol is None:
            continue
        typ = _callable_type_from_method_symbol(ctx, owner, symbol.node)
        if typ is not None:
            return typ.copy_modified(name=name)
    return None


def _callable_type_from_method_symbol(
    ctx: ClassDefContext,
    owner: TypeInfo,
    node: Any,
) -> CallableType | None:
    if isinstance(node, Decorator):
        typ = node.func.type or node.var.type
    else:
        typ = getattr(node, "type", None)
    typ = get_proper_type(typ)
    if not isinstance(typ, CallableType):
        return None
    typ = _strip_receiver_arg(owner, typ)
    typ = _resolve_receiver_return_type(ctx, owner, typ)
    return typ.copy_modified(fallback=ctx.api.named_type("builtins.function"))


def _resolve_receiver_return_type(
    ctx: ClassDefContext,
    owner: TypeInfo,
    typ: CallableType,
) -> CallableType:
    ret = get_proper_type(typ.ret_type)
    if not isinstance(ret, UnboundType):
        return typ
    assert owner.module_name
    fullname = ret.name if "." in ret.name else f"{owner.module_name}.{ret.name}"
    ti = _lookup_typeinfo(ctx, fullname)
    if ti is None:
        return typ
    return typ.copy_modified(ret_type=fill_typevars(ti))


def _strip_receiver_arg(owner: TypeInfo, typ: CallableType) -> CallableType:
    if not typ.arg_types:
        return typ
    first_name = typ.arg_names[0]
    first_type = get_proper_type(typ.arg_types[0])
    if first_name in {"self", "cls"} or (
        isinstance(first_type, Instance)
        and owner in getattr(first_type.type, "mro", [])
    ):
        return typ.copy_modified(
            arg_types=typ.arg_types[1:],
            arg_kinds=typ.arg_kinds[1:],
            arg_names=typ.arg_names[1:],
        )
    return typ


def _materialize_subcategory_helpers(ctx: ClassDefContext, info: TypeInfo) -> None:
    if info.name != "SubcategoryMethods" or "_with_axiom" in info.names:
        return
    owner = _lookup_enclosing_category_typeinfo(ctx, info)
    if owner is None:
        return
    method_type = CallableType(
        [ctx.api.named_type("builtins.str")],
        [ARG_POS],
        [None],
        fill_typevars(owner),
        ctx.api.named_type("builtins.function"),
        name="_with_axiom",
    )
    var = Var("_with_axiom", method_type)
    var.info = info
    var._fullname = f"{info.fullname}._with_axiom"
    info.names["_with_axiom"] = SymbolTableNode(MDEF, var, plugin_generated=True)


def _lookup_enclosing_category_typeinfo(
    ctx: ClassDefContext,
    info: TypeInfo,
) -> TypeInfo | None:
    return _lookup_typeinfo(ctx, info.fullname.rsplit(".", 1)[0])


def _materialize_operator_helpers(ctx: ClassDefContext, info: TypeInfo) -> None:
    if info.name == "SubcategoryMethods":
        _materialize_method(
            ctx,
            info,
            "__contains__",
            [ctx.api.named_type("builtins.object")],
            ctx.api.named_type("builtins.bool"),
        )
    elif info.name == "ElementMethods":
        _materialize_method(
            ctx,
            info,
            "__ne__",
            [ctx.api.named_type("builtins.object")],
            ctx.api.named_type("builtins.bool"),
        )


def _materialize_construction_selector_methods(
    ctx: ClassDefContext,
    info: TypeInfo,
) -> None:
    """Materialize Sage category class attributes as zero-arg selector methods."""
    for statement in ctx.cls.defs.body:
        if not isinstance(statement, AssignmentStmt) or len(statement.lvalues) != 1:
            continue
        target = statement.lvalues[0]
        if not isinstance(target, NameExpr):
            continue
        name = target.name
        construction_info = _typeinfo_from_symbol_node(
            getattr(statement.rvalue, "node", None)
        )
        if construction_info is None:
            continue
        if not _is_sage_category_typeinfo(construction_info) and not (
            _is_runtime_sage_category_fullname(construction_info.fullname)
        ):
            continue
        method_type = CallableType(
            [],
            [],
            [],
            fill_typevars(construction_info),
            ctx.api.named_type("builtins.function"),
            name=name,
        )
        var = Var(name, method_type)
        var.info = info
        var._fullname = f"{info.fullname}.{name}"
        info.names[name] = SymbolTableNode(MDEF, var, plugin_generated=True)


def _materialize_method(
    ctx: ClassDefContext,
    info: TypeInfo,
    name: str,
    arg_types: list[Instance],
    return_type: Instance,
) -> None:
    if name in info.names or _class_body_defines(ctx.cls, name):
        return
    method_type = CallableType(
        arg_types,
        [ARG_POS for _arg_type in arg_types],
        [None for _arg_type in arg_types],
        return_type,
        ctx.api.named_type("builtins.function"),
        name=name,
    )
    var = Var(name, method_type)
    var.info = info
    var._fullname = f"{info.fullname}.{name}"
    info.names[name] = SymbolTableNode(MDEF, var, plugin_generated=True)


def _is_runtime_sage_category_fullname(fullname: str) -> bool:
    from sage_mypy_category_plugin.introspection import is_sage_category_fullname

    return is_sage_category_fullname(fullname)


def _class_body_defines(cls: ClassDef, name: str) -> bool:
    for statement in cls.defs.body:
        if isinstance(statement, (FuncDef, Decorator, OverloadedFuncDef)):
            if statement.name == name:
                return True
    return False


def _walk_chain(container: Any, name_chain: str) -> Any | None:
    for p in name_chain.split("."):
        if not hasattr(container, "names"):
            return None
        st = container.names.get(p)
        if st is None or st.node is None:
            return None
        container = _typeinfo_from_symbol_node(st.node) or st.node
    if isinstance(container, TypeInfo):
        return container
    return None


def _typeinfo_from_symbol_node(node: Any) -> TypeInfo | None:
    if isinstance(node, TypeInfo):
        return node
    if isinstance(node, TypeAlias):
        target = get_proper_type(node.target)
        if isinstance(target, Instance):
            return target.type
        if isinstance(target, TypeType):
            item = get_proper_type(target.item)
            if isinstance(item, Instance):
                return item.type
    if not isinstance(node, Var) or node.type is None:
        return None
    typ = get_proper_type(node.type)
    if isinstance(typ, CallableType):
        ret = get_proper_type(typ.ret_type)
        if isinstance(ret, Instance):
            return ret.type
    if isinstance(typ, TypeType):
        item = get_proper_type(typ.item)
        if isinstance(item, Instance):
            return item.type
    return None


def _lookup_symbol_typeinfo(api: Any, fullname: str) -> TypeInfo | None:
    symbol = api.lookup_fully_qualified(fullname)
    return _typeinfo_from_symbol_node(symbol.node)


def _instance_for_typeinfo(info: TypeInfo) -> Instance:
    any_type = AnyType(TypeOfAny.special_form)
    return Instance(info, [any_type] * len(info.defn.type_vars))


def _method_container_alias_provider_typeinfo(
    api: Any,
    fullname: str,
) -> TypeInfo | None:
    source = _lookup_symbol_typeinfo(api, fullname)
    if source is not None and source.fullname == fullname:
        return source

    owner_fullname, _, method_kind = fullname.rpartition(".")
    if not owner_fullname or method_kind not in _METHOD_KINDS:
        return source

    owner = _lookup_symbol_typeinfo(api, owner_fullname)
    if owner is None:
        return source

    provider = _assigned_method_container_typeinfo(api, owner, method_kind)
    if provider is None:
        return source

    owner.names[method_kind] = SymbolTableNode(
        MDEF,
        provider,
        plugin_generated=True,
    )
    return provider


def _method_container_alias_provider_fullname(
    api: Any,
    fullname: str,
) -> str | None:
    owner_fullname, _, method_kind = fullname.rpartition(".")
    if not owner_fullname or method_kind not in _METHOD_KINDS:
        return None

    owner = _lookup_symbol_typeinfo(api, owner_fullname)
    if owner is None:
        return None
    return _assigned_method_container_fullname(owner, method_kind)


def _assigned_method_container_typeinfo(
    api: Any,
    owner: TypeInfo,
    method_kind: str,
) -> TypeInfo | None:
    symbol = owner.names.get(method_kind)
    if symbol is not None:
        provider = _typeinfo_from_symbol_node(symbol.node)
        if provider is not None:
            return provider

    for statement in getattr(owner.defn.defs, "body", ()):
        if not isinstance(statement, AssignmentStmt) or len(statement.lvalues) != 1:
            continue
        target = statement.lvalues[0]
        if not isinstance(target, NameExpr) or target.name != method_kind:
            continue
        provider = _typeinfo_from_symbol_node(getattr(statement.rvalue, "node", None))
        if provider is not None:
            return provider
        helper_name = _assigned_method_container_name(statement.rvalue)
        if helper_name is None:
            continue
        return _lookup_symbol_typeinfo(api, f"{owner.module_name}.{helper_name}")
    return None


def _assigned_method_container_fullname(
    owner: TypeInfo,
    method_kind: str,
) -> str | None:
    symbol = owner.names.get(method_kind)
    if symbol is not None:
        provider = _typeinfo_from_symbol_node(symbol.node)
        if provider is not None:
            return provider.fullname

    for statement in getattr(owner.defn.defs, "body", ()):
        if not isinstance(statement, AssignmentStmt) or len(statement.lvalues) != 1:
            continue
        target = statement.lvalues[0]
        if not isinstance(target, NameExpr) or target.name != method_kind:
            continue
        provider = _typeinfo_from_symbol_node(getattr(statement.rvalue, "node", None))
        if provider is not None:
            return provider.fullname
        helper_name = _assigned_method_container_name(statement.rvalue)
        if helper_name is not None:
            return f"{owner.module_name}.{helper_name}"
    return None


def _resolve_method_container_aliases_from_mypy(
    module: Any,
    source_fullname: str,
) -> tuple[str, ...]:
    if module is None or not hasattr(module, "defs"):
        return ()

    source_name = source_fullname.rsplit(".", 1)[-1]
    statements = module.defs.body if hasattr(module.defs, "body") else module.defs
    module_fullname = getattr(module, "fullname", "")
    aliases: list[str] = []
    for statement in statements:
        if not isinstance(statement, ClassDef):
            continue
        owner = statement
        for kind in _METHOD_KINDS:
            if not _class_assigns_method_container(owner, kind, source_name):
                continue
            owner_fullname = owner.fullname or ".".join(
                part for part in (module_fullname, owner.name) if part
            )
            aliases.append(f"{owner_fullname}.{kind}")
    return tuple(dict.fromkeys(aliases))


def _class_assigns_method_container(owner: ClassDef, kind: str, source_name: str) -> bool:
    for statement in owner.defs.body:
        if not isinstance(statement, AssignmentStmt):
            continue
        if len(statement.lvalues) != 1:
            continue
        target = statement.lvalues[0]
        if not isinstance(target, NameExpr) or target.name != kind:
            continue
        if _assigned_method_container_name(statement.rvalue) == source_name:
            return True
    return False


def _assigned_method_container_name(expr: Any) -> str | None:
    if isinstance(expr, NameExpr):
        return expr.name
    if isinstance(expr, MemberExpr):
        return expr.name
    return None


def _recover_method_helper_bindings(
    api: Any,
    module: Any,
    info: TypeInfo,
    *,
    materialize: bool,
) -> None:
    if module is None:
        return
    bindings = _method_container_symbol_bindings(module)
    helpers = {
        helper_name
        for _target_fullname, _target_name, helper_name, _is_postbind in bindings
    }
    _mark_bound_helpers(module, helpers)
    _filter_bound_helper_non_method_errors(api.errors, module, helpers)
    _filter_postbind_method_assign_errors(api.errors, module, bindings)

    for target_fullname, target_name, helper_name, is_postbind in bindings:
        if target_fullname != info.fullname:
            continue
        helper_symbol = _module_symbol(module, helper_name)
        if helper_symbol is None or helper_symbol.node is None:
            continue
        if is_postbind:
            if materialize:
                wrapper = _postbind_wrapper_kind(
                    module,
                    target_fullname,
                    target_name,
                    helper_name,
                )
                info.names[target_name] = SymbolTableNode(
                    MDEF,
                    _method_container_var(
                        target_name,
                        helper_symbol.node,
                        info,
                        api,
                        wrapper,
                    ),
                    plugin_generated=True,
                )
            continue
        existing = info.names.get(target_name)
        if existing is not None and existing.node is not None:
            _copy_helper_flags(helper_symbol.node, existing.node)


def _mark_bound_helpers(module: Any, helpers: set[str]) -> None:
    for helper_name in helpers:
        symbol = _module_symbol(module, helper_name)
        if symbol is not None and symbol.node is not None:
            _mark_helper_node(symbol.node)


def _mark_helper_node(node: Any) -> None:
    if isinstance(node, Decorator):
        if _decorator_has_name(node, {"typing.final", "typing_extensions.final"}):
            node.func.is_final = True
            node.var.is_final = True
        if _decorator_has_name(node, {"abc.abstractmethod"}):
            node.func.abstract_status = IS_ABSTRACT


def _copy_helper_flags(source: Any, target: Any) -> None:
    source_func = source.func if isinstance(source, Decorator) else source
    if getattr(source_func, "is_final", False):
        if isinstance(target, Var):
            target.is_final = True
        elif isinstance(target, Decorator):
            target.func.is_final = True
            target.var.is_final = True
    if getattr(source_func, "abstract_status", 0) == IS_ABSTRACT:
        if isinstance(target, Decorator):
            target.func.abstract_status = IS_ABSTRACT


def _filter_bound_helper_non_method_errors(
    errors: Any,
    module: Any,
    helpers: set[str],
) -> None:
    helper_lines = set(_decorated_helper_lines(module, helpers))
    if not helper_lines:
        return
    for path, items in list(getattr(errors, "error_info_map", {}).items()):
        filtered = [
            error
            for error in items
            if not _is_bound_helper_non_method_error(error, helper_lines)
        ]
        if filtered:
            errors.error_info_map[path] = filtered
        else:
            del errors.error_info_map[path]


def _filter_postbind_method_assign_errors(
    errors: Any,
    module: Any,
    bindings: tuple[tuple[str, str, str, bool], ...],
) -> None:
    assignment_lines = set(_postbind_binding_lines(module, bindings))
    assignment_lines.update(_class_body_method_container_binding_lines(module, bindings))
    if not assignment_lines:
        return
    for path, items in list(getattr(errors, "error_info_map", {}).items()):
        filtered = [
            error
            for error in items
            if not (
                getattr(error, "line", None) in assignment_lines
                and (
                    getattr(error, "message", None) == "Cannot assign to a method"
                    or str(getattr(error, "message", "")).startswith(
                        "Incompatible types in assignment"
                    )
                )
            )
        ]
        if filtered:
            errors.error_info_map[path] = filtered
        else:
            del errors.error_info_map[path]


def _filter_constructors_no_redef_errors(errors: Any, module: Any) -> None:
    lines = set(_constructors_method_lines(module))
    if not lines:
        return
    for path, items in list(getattr(errors, "error_info_map", {}).items()):
        filtered = [
            error
            for error in items
            if not (
                getattr(error, "line", None) in lines
                and str(getattr(error, "message", "")).startswith(
                    'Name "Constructors" already defined'
                )
            )
        ]
        if filtered:
            errors.error_info_map[path] = filtered
        else:
            del errors.error_info_map[path]


def _completion_self_return_base_tis(
    ctx: ClassDefContext,
    cls: ClassDef,
    info: TypeInfo,
) -> list[TypeInfo]:
    if not _looks_like_method_container(info.name):
        return []
    base_tis: list[TypeInfo] = []
    for statement in cls.defs.body:
        func = statement.func if isinstance(statement, Decorator) else statement
        if not isinstance(func, FuncDef) or func.name != "completion":
            continue
        if not _has_self_return(func.body):
            continue
        typ = get_proper_type(func.type)
        if not isinstance(typ, CallableType):
            continue
        ti = _completion_return_typeinfo(ctx, info, typ)
        if ti is None:
            continue
        if ti.fullname != info.fullname and _looks_like_method_container(ti.name):
            _recover_method_helper_bindings(
                ctx.api,
                ctx.api.modules.get(ti.module_name),
                ti,
                materialize=True,
            )
            base_tis.append(ti)
    return _prune_redundant_projected_bases(base_tis, [])


def _completion_return_typeinfo(
    ctx: ClassDefContext,
    info: TypeInfo,
    typ: CallableType,
) -> TypeInfo | None:
    ret = get_proper_type(typ.ret_type)
    if isinstance(ret, Instance):
        return ret.type
    if isinstance(ret, UnboundType):
        return (
            _lookup_typeinfo(ctx, f"{info.module_name}.{ret.name}")
            or _lookup_typeinfo(ctx, ret.name)
        )
    return None


def _has_completion_self_return(cls: ClassDef, info: TypeInfo) -> bool:
    if not _looks_like_method_container(info.name):
        return False
    for statement in cls.defs.body:
        func = statement.func if isinstance(statement, Decorator) else statement
        if isinstance(func, FuncDef) and func.name == "completion":
            return _has_self_return(func.body)
    return False


def _has_self_return(node: Any) -> bool:
    body = node.body if isinstance(node, Block) else getattr(node, "body", [])
    for statement in body:
        if isinstance(statement, ReturnStmt):
            expr = statement.expr
            if isinstance(expr, NameExpr) and expr.name == "self":
                return True
        elif isinstance(statement, IfStmt):
            for nested in statement.body:
                if _has_self_return(nested):
                    return True
            if statement.else_body is not None:
                if _has_self_return(statement.else_body):
                    return True
        elif isinstance(statement, Block):
            if _has_self_return(statement):
                return True
    return False


def _constructors_method_lines(module: Any) -> tuple[int, ...]:
    lines: list[int] = []
    for class_def in _module_statements(module):
        if not isinstance(class_def, ClassDef):
            continue
        has_collector = any(
            isinstance(statement, ClassDef) and statement.name == "Constructors"
            for statement in class_def.defs.body
        )
        if not has_collector:
            continue
        for statement in class_def.defs.body:
            if isinstance(statement, FuncDef) and statement.name == "Constructors":
                lines.append(statement.line)
    return tuple(lines)


def _postbind_binding_lines(
    module: Any,
    bindings: tuple[tuple[str, str, str, bool], ...],
) -> tuple[int, ...]:
    postbind_targets = {
        (target_fullname, target_name, helper_name)
        for target_fullname, target_name, helper_name, is_postbind in bindings
        if is_postbind
    }
    if not postbind_targets:
        return ()
    top_level_classes = {
        statement.name: statement
        for statement in _module_statements(module)
        if isinstance(statement, ClassDef)
    }
    aliases = _category_method_container_aliases(module, top_level_classes)
    module_fullname = getattr(module, "fullname", "")
    lines: list[int] = []
    for statement in _module_statements(module):
        if not isinstance(statement, AssignmentStmt) or len(statement.lvalues) != 1:
            continue
        target = _postbound_target(module_fullname, statement.lvalues[0])
        helper_name = _helper_name_from_expr(statement.rvalue)
        if target is None or helper_name is None:
            continue
        target_fullname, target_name = target
        if (
            _is_method_container_fullname(target_fullname, aliases)
            and (target_fullname, target_name, helper_name) in postbind_targets
        ):
            lines.append(statement.line)

    # Also scan inside category class bodies.
    for class_def in top_level_classes.values():
        for kind in _METHOD_KINDS:
            for statement in class_def.defs.body:
                if not isinstance(statement, AssignmentStmt) or len(statement.lvalues) != 1:
                    continue
                target = statement.lvalues[0]
                if not isinstance(target, NameExpr) or target.name != kind:
                    continue
                helper_name = _assigned_method_container_name(statement.rvalue)
                if helper_name is None:
                    continue
                target_fullname = f"{_fullname_for_class(module_fullname, class_def)}.{kind}"
                if (target_fullname, kind, helper_name) in postbind_targets:
                    lines.append(statement.line)

    return tuple(lines)


def _class_body_method_container_binding_lines(
    module: Any,
    bindings: tuple[tuple[str, str, str, bool], ...],
) -> tuple[int, ...]:
    class_body_targets = {
        (target_fullname, target_name, helper_name)
        for target_fullname, target_name, helper_name, is_postbind in bindings
        if not is_postbind and target_name in _METHOD_KINDS
    }
    if not class_body_targets:
        return ()
    module_fullname = getattr(module, "fullname", "")
    lines: list[int] = []
    for statement in _module_statements(module):
        if not isinstance(statement, ClassDef):
            continue
        target_fullname = _fullname_for_class(module_fullname, statement)
        for nested in statement.defs.body:
            if not isinstance(nested, AssignmentStmt) or len(nested.lvalues) != 1:
                continue
            target = nested.lvalues[0]
            if not isinstance(target, NameExpr):
                continue
            helper_name = _helper_name_from_expr(nested.rvalue)
            if helper_name is None:
                continue
            if (target_fullname, target.name, helper_name) in class_body_targets:
                lines.append(nested.line)
    return tuple(lines)


def _method_container_var(
    name: str,
    helper_node: Any,
    info: TypeInfo,
    api: Any,
    wrapper: str | None,
) -> Var:
    var = Var(name)
    var._fullname = f"{info.fullname}.{name}"
    var.info = info
    var.is_initialized_in_class = True
    if wrapper == "builtins.property":
        var.type = api.named_type("builtins.property")
        var.is_property = True
        return var
    if wrapper == "builtins.classmethod":
        var.type = _classmethod_type_from_helper(helper_node, api)
        return var
    if isinstance(helper_node, Decorator):
        var.type = _normalize_synthetic_var_type(
            helper_node.var.type or helper_node.func.type,
            api,
        )
        var.is_final = helper_node.var.is_final
        var.is_property = helper_node.var.is_property
        var.is_settable_property = helper_node.var.is_settable_property
        var.is_classmethod = helper_node.var.is_classmethod
        var.is_staticmethod = helper_node.var.is_staticmethod
    elif isinstance(helper_node, OverloadedFuncDef):
        var.type = _overloaded_type_from_helper(helper_node, api)
    else:
        var.type = _normalize_synthetic_var_type(getattr(helper_node, "type", None), api)
        if getattr(helper_node, "is_final", False):
            var.is_final = True
    return var


def _normalize_synthetic_var_type(typ: Any, api: Any) -> Any:
    if isinstance(typ, CallableType):
        return typ.copy_modified(fallback=api.named_type("builtins.function"))
    if isinstance(typ, Overloaded):
        return Overloaded([
            _normalize_synthetic_var_type(item, api)
            for item in typ.items
            if isinstance(item, CallableType)
        ])
    return typ


def _overloaded_type_from_helper(helper_node: OverloadedFuncDef, api: Any) -> Overloaded:
    if isinstance(helper_node.type, Overloaded):
        return _normalize_synthetic_var_type(helper_node.type, api)
    return Overloaded([
        _normalize_synthetic_var_type(item.func.type, api)
        for item in helper_node.items
        if isinstance(item, Decorator) and isinstance(item.func.type, CallableType)
    ])


def _classmethod_type_from_helper(helper_node: Any, api: Any) -> Any:
    typ = _helper_callable_type(helper_node)
    if typ is None:
        return None
    owner_type = api.named_type("builtins.object")
    if typ.arg_types:
        first_arg = get_proper_type(typ.arg_types[0])
        if isinstance(first_arg, TypeType):
            item = get_proper_type(first_arg.item)
            if isinstance(item, Instance):
                owner_type = item
    params = Parameters(
        typ.arg_types[1:],
        typ.arg_kinds[1:],
        typ.arg_names[1:],
    )
    return api.named_type("builtins.classmethod", [owner_type, params, typ.ret_type])


def _helper_callable_type(helper_node: Any) -> CallableType | None:
    if isinstance(helper_node, Decorator):
        typ = helper_node.func.type or helper_node.var.type
    else:
        typ = getattr(helper_node, "type", None)
    typ = get_proper_type(typ)
    return typ if isinstance(typ, CallableType) else None


def _postbind_wrapper_kind(
    module: Any,
    target_fullname: str,
    target_name: str,
    helper_name: str,
) -> str | None:
    module_fullname = getattr(module, "fullname", "")
    for statement in _module_statements(module):
        if not isinstance(statement, AssignmentStmt) or len(statement.lvalues) != 1:
            continue
        target = _postbound_target(module_fullname, statement.lvalues[0])
        if target != (target_fullname, target_name):
            continue
        if _helper_name_from_expr(statement.rvalue) != helper_name:
            continue
        if isinstance(statement.rvalue, CallExpr):
            callee = statement.rvalue.callee
            if isinstance(callee, RefExpr):
                return callee.fullname or callee.name
    return None


def _is_bound_helper_non_method_error(error: Any, helper_lines: set[int]) -> bool:
    return (
        getattr(error, "line", None) in helper_lines
        and getattr(error, "message", None)
        in {
            "@final cannot be used with non-method functions",
            '"abstractmethod" used with a non-method',
        }
    )


def _decorated_helper_lines(module: Any, helpers: set[str]) -> tuple[int, ...]:
    lines: list[int] = []
    for statement in _module_statements(module):
        if isinstance(statement, Decorator) and statement.name in helpers:
            lines.append(statement.line)
    return tuple(lines)


def _decorator_has_name(decorator: Decorator, fullnames: set[str]) -> bool:
    for item in decorator.original_decorators:
        if isinstance(item, RefExpr) and item.fullname in fullnames:
            return True
    return False


def _method_container_symbol_bindings(module: Any) -> tuple[tuple[str, str, str, bool], ...]:
    module_fullname = getattr(module, "fullname", "")
    top_level_classes = {
        statement.name: statement
        for statement in _module_statements(module)
        if isinstance(statement, ClassDef)
    }
    aliases = _category_method_container_aliases(module, top_level_classes)

    bindings: list[tuple[str, str, str, bool]] = []
    for class_name, class_def in top_level_classes.items():
        if _looks_like_method_container(class_name):
            target_fullname = _fullname_for_class(module_fullname, class_def)
            bindings.extend(_class_body_helper_bindings(class_def, target_fullname))
        for nested in class_def.defs.body:
            if not isinstance(nested, ClassDef) or nested.name not in _METHOD_KINDS:
                continue
            target_fullname = _fullname_for_class(module_fullname, nested)
            bindings.extend(_class_body_helper_bindings(nested, target_fullname))

    for statement in _module_statements(module):
        if not isinstance(statement, AssignmentStmt) or len(statement.lvalues) != 1:
            continue
        target = _postbound_target(module_fullname, statement.lvalues[0])
        helper_name = _helper_name_from_expr(statement.rvalue)
        if target is None or helper_name is None:
            continue
        target_fullname, target_name = target
        if _is_method_container_fullname(target_fullname, aliases):
            bindings.append((target_fullname, target_name, helper_name, True))

    for class_def in top_level_classes.values():
        target_fullname = _fullname_for_class(module_fullname, class_def)
        for statement in class_def.defs.body:
            if not isinstance(statement, AssignmentStmt) or len(statement.lvalues) != 1:
                continue
            target = statement.lvalues[0]
            if not isinstance(target, NameExpr) or target.name not in _METHOD_KINDS:
                continue
            helper_name = _helper_name_from_expr(statement.rvalue)
            if helper_name is None:
                continue
            bindings.append((target_fullname, target.name, helper_name, False))

    return tuple(dict.fromkeys(bindings))


def _category_method_container_aliases(
    module: Any,
    top_level_classes: dict[str, ClassDef],
) -> frozenset[str]:
    module_fullname = getattr(module, "fullname", "")
    aliases: set[str] = set()
    for class_def in top_level_classes.values():
        for statement in class_def.defs.body:
            if not isinstance(statement, AssignmentStmt) or len(statement.lvalues) != 1:
                continue
            target = statement.lvalues[0]
            if not isinstance(target, NameExpr) or target.name not in _METHOD_KINDS:
                continue
            alias_name = _assigned_method_container_name(statement.rvalue)
            if alias_name is None or alias_name not in top_level_classes:
                continue
            aliases.add(_fullname_for_class(module_fullname, top_level_classes[alias_name]))
    return frozenset(aliases)


def _class_body_helper_bindings(
    class_def: ClassDef,
    target_fullname: str,
) -> list[tuple[str, str, str, bool]]:
    bindings: list[tuple[str, str, str, bool]] = []
    for statement in class_def.defs.body:
        if not isinstance(statement, AssignmentStmt) or len(statement.lvalues) != 1:
            continue
        target = statement.lvalues[0]
        if not isinstance(target, NameExpr):
            continue
        helper_name = _helper_name_from_expr(statement.rvalue)
        if helper_name is None:
            continue
        bindings.append((target_fullname, target.name, helper_name, False))
    return bindings


def _postbound_target(module_fullname: str, expr: Any) -> tuple[str, str] | None:
    if not isinstance(expr, MemberExpr):
        return None
    target_name = expr.name
    class_path = _member_path(expr.expr)
    if not class_path:
        return None
    target_fullname = ".".join(part for part in (module_fullname, ".".join(class_path)) if part)
    return target_fullname, target_name


def _member_path(expr: Any) -> tuple[str, ...] | None:
    if isinstance(expr, NameExpr):
        return (expr.name,)
    if isinstance(expr, MemberExpr):
        base = _member_path(expr.expr)
        if base is None:
            return None
        return (*base, expr.name)
    return None


def _helper_name_from_expr(expr: Any) -> str | None:
    if isinstance(expr, RefExpr):
        return expr.name
    if isinstance(expr, CallExpr) and expr.args:
        return _helper_name_from_expr(expr.args[0])
    return None


def _is_method_container_fullname(
    fullname: str,
    aliases: frozenset[str],
) -> bool:
    return fullname in aliases or fullname.rsplit(".", 1)[-1] in _METHOD_KINDS


def _class_is_postbind_helper(module: Any, fullname: str) -> bool:
    """Return True if *fullname* is used as a postbind method container assignment."""
    short_name = fullname.rsplit(".", 1)[-1]
    module_fullname = getattr(module, "fullname", "")
    top_level_classes = {
        statement.name: statement
        for statement in _module_statements(module)
        if isinstance(statement, ClassDef)
    }

    for owner in top_level_classes.values():
        for statement in owner.defs.body:
            if not isinstance(statement, AssignmentStmt):
                continue
            if len(statement.lvalues) != 1:
                continue
            target = statement.lvalues[0]
            if not isinstance(target, NameExpr) or target.name not in _METHOD_KINDS:
                continue
            rhs_name = _assigned_method_container_name(statement.rvalue)
            if rhs_name == short_name and rhs_name in top_level_classes:
                rhs_class = top_level_classes[rhs_name]
                rhs_fullname = _fullname_for_class(module_fullname, rhs_class)
                if fullname == rhs_fullname:
                    return True
    return False


def _inject_postbind_helper_bases(
    ctx: ClassDefContext, info: TypeInfo, fullname: str,
) -> None:
    """Inject the base method container TypeInfo into info.mro for a postbind helper."""
    module = ctx.api.modules.get(info.module_name)
    if module is None:
        for mod_key, mod in ctx.api.modules.items():
            if mod_key.endswith(info.module_name) or info.module_name.endswith(mod_key):
                module = mod
                break
    if module is None:
        return
    module_fullname = getattr(module, "fullname", "")
    top_level_classes = {
        statement.name: statement
        for statement in _module_statements(module)
        if isinstance(statement, ClassDef)
    }
    short_name = fullname.rsplit(".", 1)[-1]

    for owner in top_level_classes.values():
        for statement in owner.defs.body:
            if not isinstance(statement, AssignmentStmt):
                continue
            if len(statement.lvalues) != 1:
                continue
            target = statement.lvalues[0]
            if not isinstance(target, NameExpr) or target.name not in _METHOD_KINDS:
                continue
            rhs_name = _assigned_method_container_name(statement.rvalue)
            if rhs_name != short_name:
                continue
            # owner is the category class doing the postbind.
            owner_ti = _lookup_typeinfo(ctx, _fullname_for_class(module_fullname, owner))
            if owner_ti is None:
                continue
            method_kind = target.name
            # Walk owner's Python MRO to find base category's method container.
            for base in getattr(owner_ti, "mro", [])[1:]:
                if base.fullname == "builtins.object":
                    break
                container_fn = f"{base.fullname}.{method_kind}"
                base_ti = _lookup_typeinfo(ctx, container_fn)
                if base_ti is None or base_ti.fullname == info.fullname:
                    continue
                # Splice base_ti into info.mro
                if base_ti not in info.mro:
                    info.mro = info.mro[:-1] + [base_ti] + [info.mro[-1]]
                return


def _inject_class_body_method_container_bases(
    ctx: ClassDefContext,
    owner_info: TypeInfo,
    module: Any,
) -> None:
    module_fullname = getattr(module, "fullname", "")
    for statement in ctx.cls.defs.body:
        if not isinstance(statement, AssignmentStmt) or len(statement.lvalues) != 1:
            continue
        target = statement.lvalues[0]
        if not isinstance(target, NameExpr) or target.name not in _METHOD_KINDS:
            continue
        helper_name = _assigned_method_container_name(statement.rvalue)
        if helper_name is None:
            continue
        helper_ti = _lookup_typeinfo(ctx, ".".join((module_fullname, helper_name)))
        if helper_ti is None:
            continue
        method_kind = target.name
        owner_info.names[method_kind] = SymbolTableNode(
            MDEF,
            helper_ti,
            plugin_generated=True,
        )
        for base in getattr(owner_info, "mro", [])[1:]:
            if base.fullname == "builtins.object":
                break
            base_ti = _lookup_typeinfo(ctx, f"{base.fullname}.{method_kind}")
            if base_ti is None or base_ti.fullname == helper_ti.fullname:
                continue
            _append_typeinfo_base(helper_ti, base_ti)
            break


def _append_typeinfo_base(info: TypeInfo, base_ti: TypeInfo) -> None:
    if base_ti.fullname in {base.type.fullname for base in info.bases}:
        return
    if base_ti in getattr(info, "mro", [])[1:]:
        return
    retained_bases = [
        base for base in info.bases if base.type.fullname != "builtins.object"
    ]
    retained_bases.append(fill_typevars(base_ti))
    info.bases = retained_bases
    info.mro = []
    calculate_mro(info)


def _fullname_for_class(module_fullname: str, class_def: ClassDef) -> str:
    return class_def.fullname or ".".join(
        part for part in (module_fullname, class_def.name) if part
    )


def _module_symbol(module: Any, name: str) -> SymbolTableNode | None:
    names = getattr(module, "names", None)
    if names is None:
        return None
    return names.get(name)


def _module_statements(module: Any) -> list[Any]:
    defs = getattr(module, "defs", [])
    return defs.body if hasattr(defs, "body") else defs
