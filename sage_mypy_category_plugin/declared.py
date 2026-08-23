"""Project a functor-declared category framework into provider projections.

Sage builds a provider surface by C3 over `ParentMethods` across super-categories,
so the runtime named class carries that surface in its own `__mro__` and the Sage
oracle traces `Category._make_named_class` to read it.

A framework whose categories select structural functors builds the same surface a
different way. Its compiler installs forwarding descriptors on a generated type,
and the supercategory never enters that type's `__mro__`: a method resolves by
following the functor to the object's image, not by Python inheritance. Reading
`__mro__` would therefore project nothing at all.

The compiler is the runtime oracle here, as `Category._make_named_class` is for
Sage. It reports, per role, the implementation types each category's selected
functors reach, which is exactly the relation its forwarding follows.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from sage_mypy_category_plugin.imports import importable_module_name_or_none
from sage_mypy_category_plugin.projection import ProviderProjection, ProviderRole

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import ModuleType

# The report keys a compiler uses for its three implementation surfaces, mapped
# onto the provider roles this plugin already names.
ROLE_FOR_SURFACE: dict[str, ProviderRole] = {
    "object": "parent",
    "element": "element",
    "arrow": "morphism",
}


@runtime_checkable
class DeclaringCompiler(Protocol):
    """A compiler that reports the inheritance its functor declarations imply."""

    def declared_inheritance(self) -> dict[str, dict[str, tuple[str, ...]]]:
        pass


def compiler_in(package_names: Sequence[str]) -> DeclaringCompiler | None:
    """Return the reporting compiler reached from the configured packages.

    Invariant I3 forbids matching a namespace by name, so this asks each member
    whether it satisfies the reporting protocol rather than looking for a known
    module or attribute name.
    """
    configured = tuple(package_names)
    module_names = tuple(
        name
        for name in configured
        if "." not in name or importable_module_name_or_none(name) == name
    )
    for module in _imported_modules(module_names):
        for name in dir(module):
            member = getattr(module, name)
            if isinstance(member, DeclaringCompiler):
                return member
            if not callable(member) or isinstance(member, type):
                continue
            # Only accessors the configured packages define. A re-exported name
            # such as a typing construct also reads as callable without an
            # argument, and calling it raises.
            if not _defined_in(member, configured):
                continue
            produced = _called_without_argument(member)
            if isinstance(produced, DeclaringCompiler):
                return produced
    return None


def _defined_in(member: object, package_names: Sequence[str]) -> bool:
    origin = getattr(member, "__module__", "")
    return any(origin == name or origin.startswith(f"{name}.") for name in package_names)


def declared_projections(
    package_names: Sequence[str],
    roles: Sequence[ProviderRole],
) -> tuple[ProviderProjection, ...]:
    """Return one projection per implementation type the compiler reports."""
    compiler = compiler_in(package_names)
    if compiler is None:
        return ()
    selected = frozenset(roles)
    reported = compiler.declared_inheritance()
    element_relations = reported.get("element", {})
    element_implementations = frozenset(
        (*element_relations, *(base for bases in element_relations.values() for base in bases))
    )
    # One implementation class can serve more than one surface: a category that
    # declares its element type as its object type reports the class under both.
    # The manifest holds one record per provider, so the surfaces merge into the
    # role that named it first, carrying every base either one reached.
    role_for_provider: dict[str, ProviderRole] = {}
    bases_for_provider: dict[str, tuple[str, ...]] = {}
    promoted_for_provider: dict[str, tuple[str, ...]] = {}
    for surface, relations in reported.items():
        role = ROLE_FOR_SURFACE.get(surface)
        if role is None or role not in selected:
            continue
        for provider, bases in relations.items():
            if provider not in role_for_provider:
                role_for_provider[provider] = role
                bases_for_provider[provider] = ()
                promoted_for_provider[provider] = ()
            recorded = bases_for_provider[provider]
            bases_for_provider[provider] = recorded + tuple(base for base in bases if base not in recorded and base != provider)
            promotable = tuple(base for base in bases if base in element_implementations)
            if promotable:
                promoted = promoted_for_provider[provider]
                promoted_for_provider[provider] = promoted + tuple(
                    base for base in promotable if base not in promoted and base != provider
                )
    # The manifest keeps the ordinary Python class graph distinct from the
    # compiler relation. The latter supplies forwarded methods and subtyping; it
    # does not make the reached implementation a Python base at runtime.
    pending = [base for bases in bases_for_provider.values() for base in bases]
    while pending:
        base = pending.pop()
        if base in bases_for_provider:
            continue
        bases_for_provider[base] = ()
        promoted_for_provider[base] = ()
        role_for_provider[base] = "parent"

    return tuple(
        ProviderProjection(
            provider=provider,
            role=role_for_provider[provider],
            runtime_class=provider,
            runtime_bases=_source_bases(provider),
            runtime_mro=_source_mro(provider),
            provider_bases=declared,
            provider_mro=_linearized(provider, bases_for_provider),
            promoted_bases=promoted_for_provider[provider],
        )
        for provider, declared in bases_for_provider.items()
    )


def _linearized(
    provider: str,
    bases_for_provider: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    """Return the transitive compiler relation for one implementation."""
    order: list[str] = [provider]
    pending = list(bases_for_provider.get(provider, ()))
    while pending:
        ancestor = pending.pop(0)
        if ancestor in order:
            continue
        order.append(ancestor)
        pending.extend(bases_for_provider.get(ancestor, ()))
    return tuple(order)


def _source_bases(provider: str) -> tuple[str, ...]:
    """Return the implementation's ordinary Python bases."""
    from sage_mypy_category_plugin.imports import import_fullname

    implementation = import_fullname(provider)
    if not isinstance(implementation, type):
        return ()
    return tuple(
        f"{base.__module__}.{base.__qualname__}"
        for base in implementation.__bases__
        if base is not object
    )


def _source_mro(provider: str) -> tuple[str, ...]:
    """Return the implementation's ordinary Python MRO."""
    from sage_mypy_category_plugin.imports import import_fullname

    implementation = import_fullname(provider)
    if not isinstance(implementation, type):
        return (provider,)
    return tuple(
        f"{ancestor.__module__}.{ancestor.__qualname__}"
        for ancestor in implementation.__mro__
        if ancestor is not object
    )


def _imported_modules(package_names: Sequence[str]) -> tuple[ModuleType, ...]:
    imported: dict[str, ModuleType] = {}
    for package_name in package_names:
        package = import_module(package_name)
        imported[package_name] = package
        for found in _submodule_names(package):
            imported[found] = import_module(found)
    return tuple(imported.values())


def _submodule_names(package: ModuleType) -> tuple[str, ...]:
    from pkgutil import walk_packages

    search_path = getattr(package, "__path__", None)
    if search_path is None:
        return ()
    return tuple(found.name for found in walk_packages(search_path, f"{package.__name__}."))


def _called_without_argument(member: object) -> object | None:
    """Return what a no-argument accessor produces, or None when it needs one.

    A framework publishes its compiler through an accessor. Selecting by
    signature keeps this from calling anything that expects arguments.
    """
    from inspect import Parameter, signature

    if not callable(member):
        return None
    parameters = signature(member).parameters.values()
    if any(
        parameter.default is Parameter.empty
        and parameter.kind not in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD)
        for parameter in parameters
    ):
        return None
    return member()
