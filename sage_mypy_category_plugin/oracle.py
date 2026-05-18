from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from importlib import import_module
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, StrictStr

import sage.all  # type: ignore[import-untyped] # noqa: F401

ProviderRole = Literal["parent", "element", "subcategory", "morphism"]


class SageCategory(Protocol):
    def all_super_categories(self, proper: bool = False) -> Sequence[SageCategory]:
        pass


@runtime_checkable
class SageCategoryFactory(Protocol):
    def an_instance(self) -> SageCategory:
        pass


class ProviderProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: StrictStr
    role: ProviderRole
    runtime_class: StrictStr
    runtime_bases: tuple[StrictStr, ...]
    runtime_mro: tuple[StrictStr, ...]
    provider_bases: tuple[StrictStr, ...]
    provider_mro: tuple[StrictStr, ...]


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


def provider_projections_for_categories(
    category_fullnames: Iterable[str],
    *,
    roles: Iterable[ProviderRole],
) -> dict[str, ProviderProjection]:
    projections: dict[str, ProviderProjection] = {}
    for category_fullname in category_fullnames:
        category_factory = _import_category_factory(category_fullname)
        category = category_factory.an_instance()
        for role in roles:
            projection = _provider_projection(category, role)
            projections[projection.provider] = projection
    return projections


def _provider_projection(category: SageCategory, role: ProviderRole) -> ProviderProjection:
    role_projection = ROLE_PROJECTIONS[role]
    runtime_class = _runtime_named_class(category, role_projection)
    provider = _provider_fullname(category, role_projection)
    runtime_to_provider = _runtime_to_provider_map(category, role_projection)
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


def _runtime_to_provider_map(
    category: SageCategory,
    role_projection: RoleProjection,
) -> dict[type[object], str]:
    categories = (category, *category.all_super_categories(proper=True))
    runtime_to_provider: dict[type[object], str] = {}
    for current_category in categories:
        runtime_class = _runtime_named_class(current_category, role_projection)
        runtime_to_provider[runtime_class] = _provider_fullname(
            current_category,
            role_projection,
        )
    return runtime_to_provider


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
) -> type[object]:
    runtime_class = getattr(category, role_projection.runtime_attr)
    assert isinstance(runtime_class, type), (
        f"{category!r}.{role_projection.runtime_attr} must be a class; "
        f"got {runtime_class!r}"
    )
    return runtime_class


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


__all__ = [
    "ProviderProjection",
    "ProviderRole",
    "provider_projections_for_categories",
]
