from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import import_module
from inspect import signature
from types import FunctionType
from typing import Literal, Protocol, Self as TypingSelf, runtime_checkable

from pydantic import BaseModel, ConfigDict

import sage.all  # type: ignore[import-untyped] # noqa: F401

from sage_mypy_category_plugin.imports import (
    import_fullname,
    importable_module_name_or_none as _importable_module_name_or_none,
)
from sage_mypy_category_plugin.projection import (
    ConcreteParentRecord,
    ProviderMethodRecord,
    ProviderProjection,
    ProviderRole,
    roles_share_projection,
)


@runtime_checkable
class SageCategory(Protocol):
    def all_super_categories(self, proper: bool = False) -> Sequence[SageCategory]:
        pass


@runtime_checkable
class SageCategoryFactory(Protocol):
    def an_instance(self) -> SageCategory:
        pass


@runtime_checkable
class SageConcreteParent(Protocol):
    def category(self) -> SageCategory:
        pass

    def _underlying_class(self) -> type[object]:
        pass


class RoleProjection(BaseModel):
    model_config = ConfigDict(frozen=True)

    runtime_attr: str
    provider_attr: str
    category_attr: str | None = None


ROLE_PROJECTIONS: Mapping[ProviderRole, RoleProjection] = {
    "parent": RoleProjection(runtime_attr="parent_class", provider_attr="ParentMethods"),
    "element": RoleProjection(runtime_attr="element_class", provider_attr="ElementMethods"),
    "subcategory": RoleProjection(
        runtime_attr="subcategory_class",
        provider_attr="SubcategoryMethods",
    ),
    "morphism": RoleProjection(
        runtime_attr="morphism_class",
        provider_attr="MorphismMethods",
    ),
    "homset_parent": RoleProjection(
        runtime_attr="parent_class",
        provider_attr="ParentMethods",
        category_attr="Homsets",
    ),
    "homset_element": RoleProjection(
        runtime_attr="element_class",
        provider_attr="ElementMethods",
        category_attr="Homsets",
    ),
}


_TRACE_SOURCE = "Category._make_named_class"
_CONCRETE_PARENT_ROLES: tuple[ProviderRole, ...] = ("parent", "element")
_PARENT_RUNTIME_RECEIVER_METHODS: Mapping[str, str] = {
    "_an_element_": "sage.structure.parent.Parent",
}


@dataclass(frozen=True)
class NamedClassTrace:
    category: str
    provider: str
    role: ProviderRole
    trace_source: str
    runtime_class: str
    runtime_bases: tuple[str, ...]
    runtime_mro: tuple[str, ...]
    runtime_attr: str
    provider_attr: str


@dataclass(frozen=True)
class UnsupportedProviderTrace:
    provider: str
    role: ProviderRole
    reason: Literal["ambiguous_runtime_mro"]
    runtime_classes: tuple[str, ...]
    runtime_mros: tuple[tuple[str, ...], ...]


_NAMED_CLASS_TRACES_BY_PROVIDER: dict[tuple[ProviderRole, str], NamedClassTrace] = {}
_UNSUPPORTED_PROVIDER_TRACES_BY_PROVIDER: dict[
    tuple[ProviderRole, str],
    UnsupportedProviderTrace,
] = {}
_RUNTIME_CLASS_BY_PROVIDER_ROLE: dict[tuple[ProviderRole, str], type[object]] = {}
_PROVIDER_CLASS_BY_FULLNAME: dict[str, type[object]] = {}
_RUNTIME_CLASS_TO_PROVIDER_BY_ROLE: dict[ProviderRole, dict[type[object], str]] = {
    role: {}
    for role in ROLE_PROJECTIONS
}
_UNPROJECTED_RUNTIME_CLASSES_BY_ROLE: dict[ProviderRole, set[type[object]]] = {
    role: set()
    for role in ROLE_PROJECTIONS
}


def provider_projections_for_categories(
    category_fullnames: Iterable[str],
    *,
    roles: Iterable[ProviderRole],
) -> dict[str, ProviderProjection]:
    _NAMED_CLASS_TRACES_BY_PROVIDER.clear()
    _UNSUPPORTED_PROVIDER_TRACES_BY_PROVIDER.clear()
    _RUNTIME_CLASS_BY_PROVIDER_ROLE.clear()
    _PROVIDER_CLASS_BY_FULLNAME.clear()
    for role in roles:
        _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role].clear()
        _UNPROJECTED_RUNTIME_CLASSES_BY_ROLE[role].clear()

    with _trace_make_named_class(roles=roles):
        projections: dict[str, ProviderProjection] = {}
        for category_fullname in category_fullnames:
            category = _import_category(category_fullname)
            for role in roles:
                projection = _provider_projection(category, role)
                if projection is not None:
                    _record_provider_projection(projections, projection)
        projections = _supported_provider_projections(projections)
        _record_discovered_runtime_provider_projections(projections)
        return projections


def _record_discovered_runtime_provider_projections(
    projections: dict[str, ProviderProjection],
) -> None:
    while pending_records := tuple(
        (role, provider, runtime_class)
        for (role, provider), runtime_class in _RUNTIME_CLASS_BY_PROVIDER_ROLE.items()
        if provider not in projections
    ):
        for role, provider, runtime_class in pending_records:
            if provider in projections:
                continue
            _record_provider_projection(
                projections,
                _provider_projection_from_runtime_class(
                    role=role,
                    provider=provider,
                    runtime_class=runtime_class,
                ),
            )


def _supported_provider_projections(
    projections: dict[str, ProviderProjection],
) -> dict[str, ProviderProjection]:
    return {
        provider: projection
        for provider, projection in projections.items()
        if not _is_unsupported_provider(projection.role, provider)
    }


def concrete_parent_records_for_factories(
    factory_fullnames: Iterable[str],
) -> dict[str, ConcreteParentRecord]:
    records, _projections = (
        concrete_parent_records_and_provider_projections_for_factories(
            factory_fullnames
        )
    )
    return records


def concrete_parent_records_and_provider_projections_for_factories(
    factory_fullnames: Iterable[str],
) -> tuple[dict[str, ConcreteParentRecord], dict[str, ProviderProjection]]:
    for role in _CONCRETE_PARENT_ROLES:
        _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role].clear()
        _UNPROJECTED_RUNTIME_CLASSES_BY_ROLE[role].clear()

    records: dict[str, ConcreteParentRecord] = {}
    with _trace_make_named_class(roles=_CONCRETE_PARENT_ROLES):
        for factory_fullname in factory_fullnames:
            factory = _import_concrete_parent_factory(factory_fullname)
            parent = factory()
            assert isinstance(parent, SageConcreteParent), (
                f"{factory_fullname!r} must construct a Sage parent with "
                "category() and _underlying_class(); got "
                f"{parent!r}"
            )
            record = _concrete_parent_record(parent)
            records[record.concrete_class] = record
    projections: dict[str, ProviderProjection] = {}
    _record_discovered_runtime_provider_projections(projections)
    return records, _supported_provider_projections(projections)


def named_class_traces() -> tuple[NamedClassTrace, ...]:
    return tuple(_NAMED_CLASS_TRACES_BY_PROVIDER.values())


def unsupported_provider_traces() -> tuple[UnsupportedProviderTrace, ...]:
    return tuple(_UNSUPPORTED_PROVIDER_TRACES_BY_PROVIDER.values())


def _record_provider_projection(
    projections: dict[str, ProviderProjection],
    projection: ProviderProjection,
) -> None:
    existing = projections.get(projection.provider)
    if existing is None:
        projections[projection.provider] = projection
        return

    assert _provider_projections_share_typeinfo(existing, projection), (
        "Conflicting provider projections for "
        f"{projection.provider}: "
        f"{existing.role} -> {existing.runtime_class} vs "
        f"{projection.role} -> {projection.runtime_class}"
    )


def _provider_projections_share_typeinfo(
    left: ProviderProjection,
    right: ProviderProjection,
) -> bool:
    return (
        roles_share_projection(left.role, right.role)
        and left.runtime_class == right.runtime_class
        and left.runtime_bases == right.runtime_bases
        and left.runtime_mro == right.runtime_mro
        and left.provider_bases == right.provider_bases
        and left.provider_mro == right.provider_mro
        and left.unprojected_runtime_mro == right.unprojected_runtime_mro
    )


def provider_method_records_for_projections(
    projections: Iterable[ProviderProjection],
    *,
    concrete_parents: Iterable[ConcreteParentRecord] = (),
) -> tuple[ProviderMethodRecord, ...]:
    records: list[ProviderMethodRecord] = []
    for projection in projections:
        provider_class = _provider_class_for_projection(projection)
        for name, member in sorted(vars(provider_class).items()):
            function = _direct_provider_function_or_none(member)
            if function is None:
                continue
            if _returns_typing_self(function):
                records.append(
                    ProviderMethodRecord(
                        provider=projection.provider,
                        name=name,
                        return_type="Self",
                    )
                )
    records.extend(_receiver_method_records_for_concrete_parents(concrete_parents))
    return _deduplicate_provider_method_records(records)


def _receiver_method_records_for_concrete_parents(
    concrete_parents: Iterable[ConcreteParentRecord],
) -> tuple[ProviderMethodRecord, ...]:
    records: list[ProviderMethodRecord] = []
    for concrete_parent in concrete_parents:
        root_parent_provider = concrete_parent.parent_provider_mro[-1]
        for method_name, owner_fullname in _PARENT_RUNTIME_RECEIVER_METHODS.items():
            if _runtime_mro_defines_method(
                concrete_parent.runtime_mro,
                method_name,
                owner_fullname=owner_fullname,
            ):
                records.append(
                    ProviderMethodRecord(
                        provider=root_parent_provider,
                        name=method_name,
                        return_type="object",
                    )
                )
    return tuple(records)


def _runtime_mro_defines_method(
    runtime_mro: tuple[str, ...],
    method_name: str,
    *,
    owner_fullname: str,
) -> bool:
    for runtime_class_fullname in runtime_mro:
        runtime_class = _importable_runtime_class_or_none(runtime_class_fullname)
        if (
            runtime_class is not None
            and _class_fullname(runtime_class) == owner_fullname
            and method_name in vars(runtime_class)
        ):
            return True
    return False


def _importable_runtime_class_or_none(fullname: str) -> type[object] | None:
    module_name = _importable_module_name_or_none(fullname)
    if module_name is None:
        return None
    qualname = fullname.removeprefix(f"{module_name}.")
    runtime_class = _resolve_module_qualname(
        module_name=module_name,
        qualname=qualname,
    )
    if not isinstance(runtime_class, type):
        return None
    return runtime_class


def _deduplicate_provider_method_records(
    records: Iterable[ProviderMethodRecord],
) -> tuple[ProviderMethodRecord, ...]:
    record_by_key: dict[tuple[str, str], ProviderMethodRecord] = {}
    for record in records:
        key = (record.provider, record.name)
        existing_record = record_by_key.get(key)
        assert existing_record is None or existing_record.return_type == record.return_type, (
            "conflicting provider method records for "
            f"{record.provider}.{record.name}: "
            f"{existing_record.return_type!r} vs {record.return_type!r}"
        )
        record_by_key[key] = record
    return tuple(record_by_key[key] for key in sorted(record_by_key))


def _provider_projection(
    category: SageCategory,
    role: ProviderRole,
) -> ProviderProjection | None:
    role_projection = ROLE_PROJECTIONS[role]
    projected_category = _projected_category(category, role_projection)
    _invalidate_named_class_cache(projected_category, role_projection)
    runtime_class = _runtime_named_class(
        projected_category,
        role_projection,
        force_recompute=True,
    )
    _ensure_runtime_class_projection(role, role_projection, runtime_class)
    for runtime_mro_class in runtime_class.__mro__:
        _ensure_runtime_class_projection(role, role_projection, runtime_mro_class)

    runtime_to_provider = _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role]
    provider = _provider_fullname_or_none(projected_category, role_projection)
    if provider is None:
        _UNPROJECTED_RUNTIME_CLASSES_BY_ROLE[role].add(runtime_class)
        return None
    if _is_unsupported_provider(role, provider):
        _UNPROJECTED_RUNTIME_CLASSES_BY_ROLE[role].add(runtime_class)
        return None

    provider_bases = _provider_bases_without_self(
        provider,
        _project_runtime_classes(
            runtime_class.__bases__,
            runtime_to_provider,
            allow_unmapped=frozenset(
                {object, *_UNPROJECTED_RUNTIME_CLASSES_BY_ROLE[role]}
            ),
        ),
    )
    provider_mro = _project_runtime_classes(
        runtime_class.__mro__,
        runtime_to_provider,
        allow_unmapped=frozenset(
            {object, *_UNPROJECTED_RUNTIME_CLASSES_BY_ROLE[role]}
        ),
    )

    assert provider_mro[0] == provider, (
        f"Projected MRO for {provider} must start with the provider itself; "
        f"got {provider_mro!r}"
    )

    return ProviderProjection(
        provider=provider,
        role=role,
        runtime_class=_class_fullname(runtime_class),
        runtime_bases=tuple(_class_fullname(base) for base in runtime_class.__bases__),
        runtime_mro=tuple(_class_fullname(base) for base in runtime_class.__mro__),
        provider_bases=provider_bases,
        provider_mro=provider_mro,
        unprojected_runtime_mro=_unprojected_runtime_classes(
            runtime_class.__mro__,
            runtime_to_provider,
        ),
    )


def _provider_projection_from_runtime_class(
    *,
    role: ProviderRole,
    provider: str,
    runtime_class: type[object],
) -> ProviderProjection:
    role_projection = ROLE_PROJECTIONS[role]
    for runtime_mro_class in runtime_class.__mro__:
        _ensure_runtime_class_projection(
            role,
            role_projection,
            runtime_mro_class,
        )

    runtime_to_provider = _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role]
    allow_unmapped: frozenset[type[object]] = frozenset(
        {object, *_UNPROJECTED_RUNTIME_CLASSES_BY_ROLE[role]}
    )
    provider_bases = _provider_bases_without_self(
        provider,
        _project_runtime_classes(
            runtime_class.__bases__,
            runtime_to_provider,
            allow_unmapped=allow_unmapped,
        ),
    )
    provider_mro = _project_runtime_classes(
        runtime_class.__mro__,
        runtime_to_provider,
        allow_unmapped=allow_unmapped,
    )
    assert provider_mro[0] == provider, (
        f"Projected MRO for {provider} must start with the provider itself; "
        f"got {provider_mro!r}"
    )
    return ProviderProjection(
        provider=provider,
        role=role,
        runtime_class=_class_fullname(runtime_class),
        runtime_bases=tuple(_class_fullname(base) for base in runtime_class.__bases__),
        runtime_mro=tuple(_class_fullname(base) for base in runtime_class.__mro__),
        provider_bases=provider_bases,
        provider_mro=provider_mro,
        unprojected_runtime_mro=_unprojected_runtime_classes(
            runtime_class.__mro__,
            runtime_to_provider,
        ),
    )


def _unprojected_runtime_classes(
    runtime_classes: tuple[type[object], ...],
    runtime_to_provider: Mapping[type[object], str],
) -> tuple[str, ...]:
    return tuple(
        _class_fullname(runtime_class)
        for runtime_class in runtime_classes
        if runtime_class not in runtime_to_provider and runtime_class is not object
    )


def _project_runtime_classes(
    runtime_classes: tuple[type[object], ...],
    runtime_to_provider: Mapping[type[object], str],
    *,
    allow_unmapped: frozenset[type[object]],
) -> tuple[str, ...]:
    unmapped = tuple(
        runtime_class
        for runtime_class in runtime_classes
        if runtime_class not in runtime_to_provider
        and runtime_class not in allow_unmapped
    )
    assert not unmapped, (
        "Could not project runtime classes to provider classes: "
        f"{tuple(_class_fullname(runtime_class) for runtime_class in unmapped)!r}"
    )
    return tuple(
        dict.fromkeys(
            runtime_to_provider[runtime_class]
            for runtime_class in runtime_classes
            if runtime_class in runtime_to_provider
        )
    )


def _provider_bases_without_self(
    provider: str,
    provider_bases: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        provider_base for provider_base in provider_bases if provider_base != provider
    )


def _provider_mro_from_runtime_mro(
    role: ProviderRole,
    runtime_mro: tuple[type[object], ...],
) -> tuple[str, ...]:
    role_projection = ROLE_PROJECTIONS[role]
    for runtime_class in runtime_mro:
        _ensure_runtime_class_projection(role, role_projection, runtime_class)

    runtime_to_provider = _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role]
    return _project_runtime_classes(
        runtime_mro,
        runtime_to_provider,
        allow_unmapped=frozenset(
            {object, *_UNPROJECTED_RUNTIME_CLASSES_BY_ROLE[role]}
        ),
    )


def _concrete_parent_record(parent: SageConcreteParent) -> ConcreteParentRecord:
    runtime_class = type(parent)
    concrete_class = parent._underlying_class()
    assert isinstance(concrete_class, type), (
        f"{parent!r}._underlying_class() must return a class; "
        f"got {concrete_class!r}"
    )

    category = parent.category()
    assert isinstance(category, SageCategory), (
        f"{parent!r}.category() must return a Sage category; got {category!r}"
    )

    parent_provider_mro = _provider_mro_from_runtime_mro(
        "parent",
        runtime_class.__mro__,
    )
    assert parent_provider_mro, (
        f"{_class_fullname(runtime_class)} must project at least one parent provider"
    )

    element_runtime_class = _element_runtime_class_from_parent(parent)
    element_provider_mro = _provider_mro_from_runtime_mro(
        "element",
        element_runtime_class.__mro__,
    )
    assert element_provider_mro, (
        f"{_class_fullname(element_runtime_class)} must project at least one "
        "element provider"
    )

    return ConcreteParentRecord(
        concrete_class=_class_fullname(concrete_class),
        runtime_class=_class_fullname(runtime_class),
        runtime_mro=tuple(_class_fullname(base) for base in runtime_class.__mro__),
        category_class=_class_fullname(type(category)),
        parent_provider_mro=parent_provider_mro,
        element_runtime_class=_class_fullname(element_runtime_class),
        element_runtime_mro=tuple(
            _class_fullname(base) for base in element_runtime_class.__mro__
        ),
        element_provider_mro=element_provider_mro,
    )


def _element_runtime_class_from_parent(parent: SageConcreteParent) -> type[object]:
    element_runtime_class = getattr(parent, "element_class", None)
    assert isinstance(element_runtime_class, type), (
        f"{parent!r}.element_class must be a class; got {element_runtime_class!r}"
    )
    return element_runtime_class


def _ensure_runtime_class_projection(
    role: ProviderRole,
    role_projection: RoleProjection,
    runtime_class: type[object],
) -> None:
    if runtime_class is object:
        return
    if runtime_class in _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role]:
        return
    if runtime_class in _UNPROJECTED_RUNTIME_CLASSES_BY_ROLE[role]:
        return

    provider = _provider_fullname_from_runtime_class_or_none(
        runtime_class,
        role_projection,
    )
    if provider is None:
        _UNPROJECTED_RUNTIME_CLASSES_BY_ROLE[role].add(runtime_class)
        return
    existing_runtime_class = _RUNTIME_CLASS_BY_PROVIDER_ROLE.get((role, provider))
    if (
        existing_runtime_class is not None
        and _class_fullname(existing_runtime_class) != _class_fullname(runtime_class)
    ):
        _record_unsupported_provider_runtime_classes(
            role=role,
            provider=provider,
            runtime_classes=(existing_runtime_class, runtime_class),
        )
        _remove_supported_provider_trace(role=role, provider=provider)
        _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role][existing_runtime_class] = provider
        _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role][runtime_class] = provider
        return
    if _is_unsupported_provider(role, provider):
        _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role][runtime_class] = provider
        return

    _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role][runtime_class] = provider
    _RUNTIME_CLASS_BY_PROVIDER_ROLE[(role, provider)] = runtime_class


def _provider_fullname_from_runtime_class_or_none(
    runtime_class: type[object],
    role_projection: RoleProjection,
) -> str | None:
    suffix = f".{role_projection.runtime_attr}"
    if not runtime_class.__qualname__.endswith(suffix):
        return None

    owner_qualname = runtime_class.__qualname__[: -len(suffix)]
    owner = _resolve_module_qualname(
        module_name=runtime_class.__module__,
        qualname=owner_qualname,
    )
    if owner is None:
        return None

    provider = vars(owner).get(role_projection.provider_attr)
    if provider is None:
        return None

    assert isinstance(provider, type), (
        f"{runtime_class.__module__}.{owner_qualname}."
        f"{role_projection.provider_attr} must be a class; got {provider!r}"
    )
    provider_fullname = _class_fullname(provider)
    _PROVIDER_CLASS_BY_FULLNAME[provider_fullname] = provider
    return provider_fullname


def _resolve_module_qualname(module_name: str, qualname: str) -> object | None:
    current: object = import_module(module_name)
    for name in qualname.split("."):
        current = getattr(current, name, None)
        if current is None:
            return None
    return current


def _provider_class_for_projection(
    projection: ProviderProjection,
) -> type[object]:
    provider_class = _PROVIDER_CLASS_BY_FULLNAME.get(projection.provider)
    assert provider_class is not None, (
        f"Provider class {projection.provider!r} was not recorded during "
        "Sage projection"
    )
    return provider_class


def _direct_provider_function_or_none(member: object) -> FunctionType | None:
    if isinstance(member, FunctionType):
        return member
    return None


def _returns_typing_self(function: FunctionType) -> bool:
    return_annotation = signature(function).return_annotation
    return return_annotation == "Self" or return_annotation is TypingSelf


def _runtime_named_class(
    category: SageCategory,
    role_projection: RoleProjection,
    *,
    force_recompute: bool = False,
) -> type[object]:
    if force_recompute and isinstance(category.__dict__, dict):
        category.__dict__.pop(role_projection.runtime_attr, None)
    runtime_class = getattr(category, role_projection.runtime_attr)
    assert isinstance(runtime_class, type), (
        f"{category!r}.{role_projection.runtime_attr} must be a class; "
        f"got {runtime_class!r}"
    )
    return runtime_class


def _projected_category(
    category: SageCategory,
    role_projection: RoleProjection,
) -> SageCategory:
    if role_projection.category_attr is None:
        return category

    category_constructor = getattr(category, role_projection.category_attr)
    projected_category = category_constructor()
    assert isinstance(projected_category, SageCategory), (
        f"{category!r}.{role_projection.category_attr}() must be a Sage category; "
        f"got {projected_category!r}"
    )
    return projected_category


def _invalidate_named_class_cache(
    category: SageCategory,
    role_projection: RoleProjection,
) -> None:
    if isinstance(category.__dict__, dict):
        category.__dict__.pop(role_projection.runtime_attr, None)


def _provider_fullname_or_none(
    category: SageCategory,
    role_projection: RoleProjection,
) -> str | None:
    provider_owner = _static_category_type(category)
    provider_class = vars(provider_owner).get(role_projection.provider_attr)
    if provider_class is None:
        return None
    assert isinstance(provider_class, type), (
        f"{_class_fullname(provider_owner)}.{role_projection.provider_attr} "
        f"must be a class; got {provider_class!r}"
    )
    provider_fullname = _class_fullname(provider_class)
    _PROVIDER_CLASS_BY_FULLNAME[provider_fullname] = provider_class
    return provider_fullname


def _record_named_class_trace(
    *,
    role: ProviderRole,
    provider: str,
    runtime_class: type[object],
    trace: NamedClassTrace,
) -> None:
    if _is_unsupported_provider(role, provider):
        _record_unsupported_provider_trace(
            role=role,
            provider=provider,
            traces=(trace,),
        )
        _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role][runtime_class] = provider
        return

    existing_trace = _NAMED_CLASS_TRACES_BY_PROVIDER.get((role, provider))
    if existing_trace is not None and not _named_class_traces_agree(
        existing_trace,
        trace,
    ):
        _record_unsupported_provider_trace(
            role=role,
            provider=provider,
            traces=(existing_trace, trace),
        )
        _remove_supported_provider_trace(role=role, provider=provider)
        _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role][runtime_class] = provider
        return

    _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role][runtime_class] = provider
    _RUNTIME_CLASS_BY_PROVIDER_ROLE[(role, provider)] = runtime_class
    _NAMED_CLASS_TRACES_BY_PROVIDER[(role, provider)] = trace


def _named_class_traces_agree(
    left: NamedClassTrace,
    right: NamedClassTrace,
) -> bool:
    return (
        left.runtime_class == right.runtime_class
        and left.runtime_bases == right.runtime_bases
        and left.runtime_mro == right.runtime_mro
        and left.runtime_attr == right.runtime_attr
        and left.provider_attr == right.provider_attr
    )


def _is_unsupported_provider(role: ProviderRole, provider: str) -> bool:
    return (role, provider) in _UNSUPPORTED_PROVIDER_TRACES_BY_PROVIDER


def _record_unsupported_provider_trace(
    *,
    role: ProviderRole,
    provider: str,
    traces: Iterable[NamedClassTrace],
) -> None:
    _record_unsupported_provider_runtime_mros(
        role=role,
        provider=provider,
        runtime_mro_by_class={
            trace.runtime_class: trace.runtime_mro for trace in traces
        },
    )


def _record_unsupported_provider_runtime_classes(
    *,
    role: ProviderRole,
    provider: str,
    runtime_classes: Iterable[type[object]],
) -> None:
    _record_unsupported_provider_runtime_mros(
        role=role,
        provider=provider,
        runtime_mro_by_class={
            _class_fullname(runtime_class): tuple(
                _class_fullname(mro_class) for mro_class in runtime_class.__mro__
            )
            for runtime_class in runtime_classes
        },
    )


def _record_unsupported_provider_runtime_mros(
    *,
    role: ProviderRole,
    provider: str,
    runtime_mro_by_class: dict[str, tuple[str, ...]],
) -> None:
    existing_trace = _UNSUPPORTED_PROVIDER_TRACES_BY_PROVIDER.get((role, provider))
    merged_runtime_mro_by_class: dict[str, tuple[str, ...]] = {}
    if existing_trace is not None:
        merged_runtime_mro_by_class.update(
            zip(
                existing_trace.runtime_classes,
                existing_trace.runtime_mros,
                strict=True,
            )
        )
    merged_runtime_mro_by_class.update(runtime_mro_by_class)
    _UNSUPPORTED_PROVIDER_TRACES_BY_PROVIDER[(role, provider)] = (
        UnsupportedProviderTrace(
            provider=provider,
            role=role,
            reason="ambiguous_runtime_mro",
            runtime_classes=tuple(merged_runtime_mro_by_class),
            runtime_mros=tuple(merged_runtime_mro_by_class.values()),
        )
    )


def _remove_supported_provider_trace(
    *,
    role: ProviderRole,
    provider: str,
) -> None:
    _NAMED_CLASS_TRACES_BY_PROVIDER.pop((role, provider), None)
    _RUNTIME_CLASS_BY_PROVIDER_ROLE.pop((role, provider), None)


def _static_category_type(category: SageCategory) -> type[object]:
    category_type = type(category)
    if category_type.__name__.endswith("_with_category"):
        return category_type.__mro__[1]
    return category_type


def _import_category(fullname: str) -> SageCategory:
    candidate = import_fullname(fullname)
    if not isinstance(candidate, type) and isinstance(candidate, SageCategory):
        return candidate

    category_factory = candidate
    assert isinstance(category_factory, SageCategoryFactory), (
        f"{fullname!r} must resolve to a Sage category factory; "
        f"got {category_factory!r}"
    )
    category = category_factory.an_instance()
    assert isinstance(category, SageCategory), (
        f"{fullname!r}.an_instance() must return a Sage category; got {category!r}"
    )
    return category


def _import_concrete_parent_factory(fullname: str) -> type[object]:
    factory = import_fullname(fullname)
    assert isinstance(factory, type), (
        f"{fullname!r} must resolve to a concrete parent class; got {factory!r}"
    )
    return factory


def _class_fullname(cls: type[object]) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


@contextmanager
def _trace_make_named_class(
    *,
    roles: Iterable[ProviderRole],
) -> Iterator[None]:
    from sage.categories.category import Category  # type: ignore[import-untyped]

    role_projections = tuple((role, ROLE_PROJECTIONS[role]) for role in roles)
    original_make_named_class = Category._make_named_class

    def traced_make_named_class(
        self: SageCategory,
        name: str,
        method_provider: str,
        cache: bool = False,
        picklable: bool = True,
    ) -> type[object]:
        runtime_class = original_make_named_class(
            self,
            name,
            method_provider,
            cache=cache,
            picklable=picklable,
        )
        matching_roles = tuple(
            role
            for role, role_projection in role_projections
            if role_projection.provider_attr == method_provider
            and role_projection.runtime_attr == name
        )
        if not matching_roles:
            return runtime_class

        for role in matching_roles:
            provider = _provider_fullname_or_none(self, ROLE_PROJECTIONS[role])
            if provider is None:
                _UNPROJECTED_RUNTIME_CLASSES_BY_ROLE[role].add(runtime_class)
                continue

            trace = NamedClassTrace(
                category=_class_fullname(type(self)),
                provider=provider,
                role=role,
                trace_source=_TRACE_SOURCE,
                runtime_class=_class_fullname(runtime_class),
                runtime_bases=tuple(
                    _class_fullname(base) for base in runtime_class.__bases__
                ),
                runtime_mro=tuple(_class_fullname(base) for base in runtime_class.__mro__),
                runtime_attr=name,
                provider_attr=method_provider,
            )
            _record_named_class_trace(
                role=role,
                provider=provider,
                runtime_class=runtime_class,
                trace=trace,
            )
        return runtime_class

    Category._make_named_class = traced_make_named_class  # type: ignore[assignment]
    try:
        yield
    finally:
        Category._make_named_class = original_make_named_class  # type: ignore[assignment]


__all__ = [
    "ConcreteParentRecord",
    "ProviderProjection",
    "ProviderRole",
    "NamedClassTrace",
    "UnsupportedProviderTrace",
    "concrete_parent_records_for_factories",
    "concrete_parent_records_and_provider_projections_for_factories",
    "named_class_traces",
    "provider_method_records_for_projections",
    "provider_projections_for_categories",
    "unsupported_provider_traces",
]
