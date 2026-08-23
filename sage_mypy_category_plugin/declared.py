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
    projections: list[ProviderProjection] = []
    for surface, relations in reported.items():
        role = ROLE_FOR_SURFACE.get(surface)
        if role is None or role not in selected:
            continue
        for provider, bases in relations.items():
            projections.append(
                ProviderProjection(
                    provider=provider,
                    role=role,
                    runtime_class=provider,
                    runtime_bases=tuple(bases),
                    runtime_mro=(provider, *bases),
                    provider_bases=tuple(bases),
                    provider_mro=(provider, *bases),
                )
            )
    return tuple(projections)


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
