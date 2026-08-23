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
    for module in _imported_modules(package_names):
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
    # One implementation class can serve more than one surface: a category that
    # declares its element type as its object type reports the class under both.
    # The manifest holds one record per provider, so the surfaces merge into the
    # role that named it first, carrying every base either one reached.
    role_for_provider: dict[str, ProviderRole] = {}
    bases_for_provider: dict[str, tuple[str, ...]] = {}
    for surface, relations in reported.items():
        role = ROLE_FOR_SURFACE.get(surface)
        if role is None or role not in selected:
            continue
        for provider, bases in relations.items():
            if provider not in role_for_provider:
                role_for_provider[provider] = role
                bases_for_provider[provider] = ()
            recorded = bases_for_provider[provider]
            bases_for_provider[provider] = recorded + tuple(base for base in bases if base not in recorded and base != provider)
    # Sage's named class carries the whole provider surface in its own bases, so
    # the projection replaces them. Here the source class is ordinary Python with
    # real bases of its own, and the declared relation is what the compiler adds
    # on top. Dropping those bases would take the class's own surface with them,
    # so each record keeps them and appends what the functors declare. A class
    # can appear both ways, so the union keeps one entry per base.
    combined_for_provider: dict[str, tuple[str, ...]] = {}
    for provider, declared in bases_for_provider.items():
        source = _source_bases(provider)
        combined_for_provider[provider] = source + tuple(
            base for base in declared if base not in source
        )

    # The manifest holds a closed graph: every class named as a base carries its
    # own record, and so does every class those records name in turn.
    pending = [base for bases in combined_for_provider.values() for base in bases]
    while pending:
        base = pending.pop()
        if base in combined_for_provider:
            continue
        combined_for_provider[base] = _source_bases(base)
        if base not in role_for_provider:
            role_for_provider[base] = "parent"
        pending.extend(combined_for_provider[base])

    return tuple(
        ProviderProjection(
            provider=provider,
            role=role_for_provider[provider],
            runtime_class=provider,
            runtime_bases=bases,
            runtime_mro=_linearized(provider, combined_for_provider),
            provider_bases=bases,
            provider_mro=_linearized(provider, combined_for_provider),
        )
        for provider, bases in combined_for_provider.items()
    )


def _linearized(
    provider: str,
    bases_for_provider: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    """Return the whole ancestry, since the plugin assigns it as the MRO.

    Listing only the direct bases would cut every class off from its
    grandparents, so a type would stop satisfying the interfaces it inherits.
    """
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
    """Return the class's own bases, which the declared relation adds to."""
    from sage_mypy_category_plugin.imports import import_fullname

    implementation = import_fullname(provider)
    if not isinstance(implementation, type):
        return ()
    return tuple(
        f"{base.__module__}.{base.__qualname__}"
        for base in implementation.__bases__
        if base is not object
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
