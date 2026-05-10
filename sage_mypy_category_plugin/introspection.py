"""
Sage introspection API for the mypy category override plugin.

This module provides the bridge between literal source-level method-container
classes (ParentMethods, ElementMethods, etc.) and Sage's dynamically constructed
class hierarchy. It asks Sage for the runtime class graph and projects the direct
base edges back onto source-level method containers.

Key invariant: for a dynamic edge C.parent_class -> D.parent_class (from
__bases__), we project C.ParentMethods -> D.ParentMethods as a static base
edge for mypy.
"""

from __future__ import annotations

import importlib
import types
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CategoryMethodContainer:
    """Parsed representation of a Sage category method container fullname.

    Examples:
        "sage.categories.rings.Rings.ParentMethods"
            → module_name="sage.categories.rings",
              category_path=("Rings",),
              method_kind="ParentMethods"

        "sage.categories.objects.Objects.Homsets.ParentMethods"
            → module_name="sage.categories.objects",
              category_path=("Objects", "Homsets"),
              method_kind="ParentMethods"
    """

    module_name: str
    category_path: tuple[str, ...]
    method_kind: str


# Accepted terminal method-container class names.
_METHOD_KINDS = frozenset({
    "ParentMethods",
    "ElementMethods",
    "MorphismMethods",
    "SubcategoryMethods",
})

# Map from source method-container class name to the corresponding Sage
# dynamic-class attribute on a category instance.
_METHOD_KIND_TO_DYN_ATTR: dict[str, str] = {
    "ParentMethods": "parent_class",
    "ElementMethods": "element_class",
    "MorphismMethods": "morphism_class",
    "SubcategoryMethods": "subcategory_class",
}


# ---------------------------------------------------------------------------
# Fullname parsing
# ---------------------------------------------------------------------------


def parse_method_container_fullname(
    fullname: str,
) -> CategoryMethodContainer | None:
    """Parse a dotted fullname into a CategoryMethodContainer, or return None.

    Splits the last component off as method_kind. The remaining components
    are interpreted as ``module_name . category_path[0] . category_path[1] ...``.

    The module must reside under ``sage.categories.``.  After the structural
    parse we attempt to import the module and verify that each element of
    ``category_path`` is a Category subclass (or, for the trailing element,
    at least that the module/class graph looks like a Sage category tree).
    If anything fails, the function returns None.

    Args:
        fullname: Dotted Python fullname, e.g.
            ``"sage.categories.rings.Rings.ParentMethods"``.

    Returns:
        A ``CategoryMethodContainer`` if the fullname represents a method
        container inside a Sage category; ``None`` otherwise.
    """
    # Structural parse only — no Sage imports. The module may not be
    # importable in mypy's process, and that's fine. Real validation
    # happens in instantiate_category_from_source_path.
    parts = fullname.split(".")
    if len(parts) < 3:
        return None

    method_kind = parts[-1]
    if method_kind not in _METHOD_KINDS:
        return None

    prefix = parts[:-1]

    # Must start with "sage.categories" structurally
    joined = ".".join(prefix)
    if not (joined.startswith("sage.categories.") or joined == "sage.categories"):
        return None

    # Find the first CamelCase / underscore-start element after
    # the "categories" segment. Everything before it is the module,
    # everything from there is the category path.
    import re
    _camel = re.compile(r'^[A-Z_]')
    cat_start = None
    for i, p in enumerate(prefix):
        if p == "categories" and i > 0 and prefix[i - 1] == "sage":
            for j in range(i + 1, len(prefix)):
                if _camel.match(prefix[j]):
                    cat_start = j
                    break
            break
    if cat_start is None:
        return None

    return CategoryMethodContainer(
        module_name=".".join(prefix[:cat_start]),
        category_path=tuple(prefix[cat_start:]),
        method_kind=method_kind,
    )


def _validate_category_path(
    mod: types.ModuleType,
    category_path: tuple[str, ...],
) -> None:
    """Raise ValueError/AttributeError if the first element of
    *category_path* is not a Category subclass accessible from *mod*.

    Only the first element is validated structurally. Subsequent elements
    (nested classes like ``Homsets``, axiom methods like ``Finite``) are
    resolved at instantiation time by
    :func:`instantiate_category_from_source_path` — they may be methods on
    category instances rather than static class attributes.
    """
    from sage.categories.category import Category

    top_name = category_path[0]
    top_obj = getattr(mod, top_name)
    if not (isinstance(top_obj, type) and issubclass(top_obj, Category)):
        raise ValueError(
            f"{top_name!r} in module {mod.__name__!r} is not a Category subclass"
        )


def is_sage_method_container(fullname: str) -> bool:
    """Return True if *fullname* identifies a Sage category method container.

    Args:
        fullname: A dotted Python fullname.

    Returns:
        ``True`` iff ``parse_method_container_fullname(fullname)`` returns a
        non-None value.
    """
    return parse_method_container_fullname(fullname) is not None


# ---------------------------------------------------------------------------
# Category instantiation
# ---------------------------------------------------------------------------


def instantiate_category_from_source_path(
    module: types.ModuleType,
    category_path: tuple[str, ...],
) -> Any:
    """Instantiate a Sage category from a source-module and category path.

    Uses ``.an_instance()`` as the preferred instantiation mechanism, falling
    back to direct construction only when ``.an_instance()`` is unavailable.

    - Flat: ``category_path = ("Rings",)`` → ``module.Rings.an_instance()``
    - Nested: ``("Objects", "Homsets")`` →
      ``module.Objects.an_instance().Homsets()``
    - Axiom: ``("Monoids", "Finite")`` →
      ``module.Monoids.an_instance().Finite()``

    Args:
        module: The Python module containing the top-level category class.
        category_path: Tuple of attribute names forming the path to the
            category, starting from *module*.

    Returns:
        A Sage category instance.

    Raises:
        AttributeError: If an attribute in the path is missing.
        TypeError: If the category cannot be instantiated (e.g. unresolved
            parameterized category without a default).
        ImportError: If Sage cannot be imported.
    """
    if not category_path:
        raise ValueError("category_path must not be empty")

    # First element: get the category class from the module.
    top_name = category_path[0]
    top_cls = getattr(module, top_name)

    # For the first element, call .an_instance() if available.
    if hasattr(top_cls, "an_instance"):
        cat = top_cls.an_instance()
    else:
        cat = top_cls()

    # Walk remaining path elements as method calls on the instance.
    for name in category_path[1:]:
        meth = getattr(cat, name)
        cat = meth()

    return cat


# ---------------------------------------------------------------------------
# Direct base projection
# ---------------------------------------------------------------------------


def _fullname_of_class(cls: type) -> str:
    """Return the dotted fullname of a class."""
    return cls.__module__ + "." + cls.__qualname__


def method_container_direct_bases(source_fullname: str) -> list[str]:
    """Return the fullnames of method containers that are direct Sage
    semantic bases of the method container identified by *source_fullname*.

    Algorithm (from design doc):

    1. Parse *source_fullname* → module_name, category_path, method_kind.
    2. Import the module, instantiate the category.
    3. Get ``C.<dyn_attr>`` (e.g. ``C.parent_class``).
    4. Read ``dynamic_class.__bases__`` (direct bases, **not** MRO).
    5. Build a lookup: for each D in ``C.all_super_categories(proper=True)``
       that has ``<dyn_attr>``, map ``D.<dyn_attr>`` → D.
    6. For each dynamic base B in ``dynamic_class.__bases__``:
       - Look up D = lookup[B].
       - If D is None, skip (``object`` or non-category base).
       - Get ``source_container = getattr(type(D), method_kind, None)``.
       - If source_container is not None, append its fullname.
    7. Deduplicate preserving order.

    Args:
        source_fullname: Dotted fullname of a method container, e.g.
            ``"sage.categories.rings.Rings.ParentMethods"``.

    Returns:
        List of method-container fullnames representing the direct bases.
        Empty list if the fullname cannot be resolved.

    Raises:
        ImportError: If Sage cannot be imported.
    """
    parsed = parse_method_container_fullname(source_fullname)
    if parsed is None:
        return []

    mod = importlib.import_module(parsed.module_name)
    try:
        cat = instantiate_category_from_source_path(mod, parsed.category_path)
    except Exception:
        # Parameterized categories (e.g. Algebras) can't be instantiated
        # without explicit arguments. Skip silently — the spec says no
        # parameter guessing.
        return []

    dyn_attr = _METHOD_KIND_TO_DYN_ATTR[parsed.method_kind]
    dynamic_class = getattr(cat, dyn_attr)

    # Direct bases from Sage's dynamic class — not MRO!
    dynamic_bases: tuple[type, ...] = dynamic_class.__bases__

    # Build lookup: D.<dyn_attr> → D for all super-categories that have it.
    candidates = cat.all_super_categories(proper=True)
    dynamic_to_category: dict[type, Any] = {}
    for D in candidates:
        if hasattr(D, dyn_attr):
            dc = getattr(D, dyn_attr)
            dynamic_to_category[dc] = D

    result: list[str] = []
    seen: set[str] = set()

    for B in dynamic_bases:
        # Skip plain ``object`` — it carries no Sage semantics.
        if B is object:
            continue

        D = dynamic_to_category.get(B)
        if D is None:
            # This can happen for non-category runtime bases or for bases
            # from categories that don't appear in all_super_categories
            # (should be rare). Skip silently — mypy will handle transitive
            # resolution when it eventually encounters the base container.
            continue

        source_container = getattr(type(D), parsed.method_kind, None)
        if source_container is None:
            continue

        fn = _fullname_of_class(source_container)
        if fn not in seen:
            seen.add(fn)
            result.append(fn)

    return result


# ---------------------------------------------------------------------------
# Module-level dependency discovery
# ---------------------------------------------------------------------------


def _find_method_containers_in_module(
    mod: types.ModuleType,
    module_fullname: str,
) -> list[str]:
    """Find literal nested method-container classes inside *mod*.

    Scans top-level names in *mod* for Category subclasses, then inspects
    those classes for nested ParentMethods / ElementMethods / etc.
    """
    from sage.categories.category import Category

    containers: list[str] = []
    for name in dir(mod):
        obj = getattr(mod, name)
        if not (isinstance(obj, type) and issubclass(obj, Category)):
            continue
        for kind in _METHOD_KINDS:
            if hasattr(obj, kind):
                container_cls = getattr(obj, kind)
                containers.append(_fullname_of_class(container_cls))
    return containers


def module_method_container_dependencies(module_fullname: str) -> list[str]:
    """Return the set of module names that contain base method containers for
    all method containers defined in *module_fullname*.

    This is used by the mypy plugin's ``get_additional_deps`` to declare
    dynamic dependencies so that incremental checking correctly invalidates
    dependents when a base container changes.

    Args:
        module_fullname: Dotted module name, e.g.
            ``"sage.categories.rings"``.

    Returns:
        Sorted, deduplicated list of module names.
    """
    mod = importlib.import_module(module_fullname)
    container_fullnames = _find_method_containers_in_module(mod, module_fullname)

    dep_modules: set[str] = set()
    for fn in container_fullnames:
        bases = method_container_direct_bases(fn)
        for base_fn in bases:
            # The module is everything before the last dot in the class fullname.
            # But the container's module is the module part of the class fullname,
            # which may differ from the module containing the category class.
            # Extract module: split on "." and take all but the last part
            # for the class qualname, but we need the module of the class.
            dep_mod = _module_of_fullname(base_fn)
            if dep_mod is not None:
                dep_modules.add(dep_mod)

    return sorted(dep_modules)


def _module_of_fullname(fullname: str) -> str | None:
    """Extract the module portion of a dotted class fullname."""
    if not fullname:
        return None
    # The class qualname may contain dots (e.g. "Rings.ParentMethods"),
    # so we can't just use rsplit(".", 1). Instead, import the class and
    # get its __module__.
    try:
        parsed = parse_method_container_fullname(fullname)
        if parsed is not None:
            return parsed.module_name
    except Exception:
        pass

    # Fallback: import the class and read __module__.
    try:
        mod_name, _qualname = _rsplit_module(fullname)
        cls = _import_class(mod_name, fullname)
        return cls.__module__
    except Exception:
        return None


def _rsplit_module(fullname: str) -> tuple[str, str]:
    """Split a dotted fullname into (module, qualname) by importing."""
    parts = fullname.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        try:
            importlib.import_module(candidate)
            return candidate, ".".join(parts[i:])
        except (ImportError, ModuleNotFoundError):
            continue
    return "", fullname


def _import_class(module_name: str, fullname: str) -> type:
    """Import a class by its fullname."""
    mod = importlib.import_module(module_name)
    # The qualname may contain dots — walk the attribute chain.
    remaining = fullname[len(module_name) + 1:]
    parts = remaining.split(".")
    obj = mod
    for part in parts:
        obj = getattr(obj, part)
    if not isinstance(obj, type):
        raise TypeError(f"{fullname!r} does not resolve to a class")
    return obj


# ---------------------------------------------------------------------------
# Debug oracle
# ---------------------------------------------------------------------------


def debug_projection(source_fullname: str) -> str:
    """Produce a human-readable debug dump of the base projection for
    *source_fullname*.

    Output format::

        C.ParentMethods static bases (from Sage):
          A.ParentMethods
          B.ParentMethods

    Args:
        source_fullname: Dotted fullname of a method container.

    Returns:
        A multi-line string showing the projected static bases.
    """
    parsed = parse_method_container_fullname(source_fullname)
    if parsed is None:
        return f"{source_fullname}: not a valid Sage method container"

    try:
        bases = method_container_direct_bases(source_fullname)
    except Exception as exc:
        return f"{source_fullname}: error during projection — {exc}"

    lines = [f"{source_fullname} static bases (from Sage):"]
    if not bases:
        lines.append("  (none)")
    else:
        for b in bases:
            lines.append(f"  {b}")

    return "\n".join(lines)
