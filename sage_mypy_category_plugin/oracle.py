from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import import_module
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

import sage.all  # type: ignore[import-untyped] # noqa: F401

from sage_mypy_category_plugin.projection import ProviderProjection, ProviderRole


class SageCategory(Protocol):
    def all_super_categories(self, proper: bool = False) -> Sequence[SageCategory]:
        pass


@runtime_checkable
class SageCategoryFactory(Protocol):
    def an_instance(self) -> SageCategory:
        pass


class RoleProjection(BaseModel):
    model_config = ConfigDict(frozen=True)

    runtime_attr: str
    provider_attr: str


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
}


_TRACE_SOURCE = "Category._make_named_class"


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


_NAMED_CLASS_TRACES_BY_PROVIDER: dict[str, NamedClassTrace] = {}
_RUNTIME_CLASS_TO_PROVIDER_BY_ROLE: dict[ProviderRole, dict[type[object], str]] = {
    role: {}
    for role in ("parent", "element", "subcategory", "morphism")
}


def provider_projections_for_categories(
    category_fullnames: Iterable[str],
    *,
    roles: Iterable[ProviderRole],
) -> dict[str, ProviderProjection]:
    _NAMED_CLASS_TRACES_BY_PROVIDER.clear()
    for role in roles:
        _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role].clear()

    with _trace_make_named_class(roles=roles):
        projections: dict[str, ProviderProjection] = {}
        for category_fullname in category_fullnames:
            category_factory = _import_category_factory(category_fullname)
            category = category_factory.an_instance()
            for role in roles:
                projection = _provider_projection(category, role)
                projections[projection.provider] = projection
        return projections


def named_class_traces() -> tuple[NamedClassTrace, ...]:
    return tuple(_NAMED_CLASS_TRACES_BY_PROVIDER.values())


def _provider_projection(category: SageCategory, role: ProviderRole) -> ProviderProjection:
    role_projection = ROLE_PROJECTIONS[role]
    _invalidate_named_class_cache(category, role_projection)
    runtime_class = _runtime_named_class(
        category,
        role_projection,
        force_recompute=True,
    )
    runtime_to_provider = _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role]
    provider = _provider_fullname(category, role_projection)
    provider_bases = _project_runtime_classes(
        runtime_class.__bases__,
        runtime_to_provider,
        allow_unmapped=frozenset({object}),
    )
    provider_mro = _project_runtime_classes(
        runtime_class.__mro__,
        runtime_to_provider,
        allow_unmapped=frozenset({object}),
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
        runtime_to_provider[runtime_class]
        for runtime_class in runtime_classes
        if runtime_class in runtime_to_provider
    )


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


def _invalidate_named_class_cache(
    category: SageCategory,
    role_projection: RoleProjection,
) -> None:
    all_categories = (category, *category.all_super_categories(proper=True))
    for current_category in all_categories:
        if isinstance(current_category.__dict__, dict):
            current_category.__dict__.pop(role_projection.runtime_attr, None)


def _provider_fullname(category: SageCategory, role_projection: RoleProjection) -> str:
    provider_class = getattr(type(category), role_projection.provider_attr)
    assert isinstance(provider_class, type), (
        f"{type(category)!r}.{role_projection.provider_attr} must be a class; "
        f"got {provider_class!r}"
    )
    return _class_fullname(provider_class)


def _import_category_factory(fullname: str) -> SageCategoryFactory:
    module_name, separator, class_name = fullname.rpartition(".")
    assert separator == ".", f"Expected fully-qualified class name, got {fullname!r}"

    module = import_module(module_name)
    category_factory = getattr(module, class_name)
    assert isinstance(category_factory, SageCategoryFactory), (
        f"{fullname!r} must resolve to a Sage category factory; "
        f"got {category_factory!r}"
    )
    return category_factory


def _class_fullname(cls: type[object]) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


@contextmanager
def _trace_make_named_class(
    *,
    roles: Iterable[ProviderRole],
) -> Iterator[None]:
    from sage.categories.category import Category  # type: ignore[import-untyped]

    role_by_provider_attr = {
        ROLE_PROJECTIONS[role].provider_attr: role for role in roles
    }
    role_by_runtime_attr = {
        ROLE_PROJECTIONS[role].runtime_attr: role for role in roles
    }
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
        role = role_by_provider_attr.get(method_provider)
        if role is None or role_by_runtime_attr.get(name) != role:
            return runtime_class

        provider = _provider_fullname(self, ROLE_PROJECTIONS[role])
        trace = NamedClassTrace(
            category=_class_fullname(type(self)),
            provider=provider,
            role=role,
            trace_source=_TRACE_SOURCE,
            runtime_class=_class_fullname(runtime_class),
            runtime_bases=tuple(_class_fullname(base) for base in runtime_class.__bases__),
            runtime_mro=tuple(_class_fullname(base) for base in runtime_class.__mro__),
            runtime_attr=name,
            provider_attr=method_provider,
        )
        _RUNTIME_CLASS_TO_PROVIDER_BY_ROLE[role][runtime_class] = provider
        _NAMED_CLASS_TRACES_BY_PROVIDER[provider] = trace
        return runtime_class

    Category._make_named_class = traced_make_named_class  # type: ignore[assignment]
    try:
        yield
    finally:
        Category._make_named_class = original_make_named_class  # type: ignore[assignment]


__all__ = [
    "ProviderProjection",
    "ProviderRole",
    "NamedClassTrace",
    "named_class_traces",
    "provider_projections_for_categories",
]
