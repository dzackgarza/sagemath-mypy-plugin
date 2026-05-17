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
import importlib.util
import logging
import re
import sys
import types
from pathlib import Path
from dataclasses import dataclass
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

_LOG = logging.getLogger(__name__)
_SAGE_INITIALIZED = False


def _ensure_sage_initialized() -> None:
    global _SAGE_INITIALIZED
    if _SAGE_INITIALIZED:
        return
    import sage.all  # noqa: F401
    _SAGE_INITIALIZED = True


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


@dataclass(frozen=True)
class MethodContainerProjection:
    source_fullname: str
    dynamic_class: str
    dynamic_bases: tuple[str, ...]
    unmapped_dynamic_bases: tuple[str, ...]
    static_bases: tuple[str, ...]


class ProjectionError(RuntimeError):
    """Base class for method-container projection failures."""


class ParameterizedCategoryError(ProjectionError):
    """Raised when a category requires explicit representative arguments."""


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

_CLASSLIKE_SEGMENT = re.compile(r"^[A-Z_]")


# ---------------------------------------------------------------------------
# Fullname parsing
# ---------------------------------------------------------------------------


def parse_method_container_fullname(
    fullname: str,
) -> CategoryMethodContainer | None:
    """Parse a dotted fullname into a CategoryMethodContainer, or return None.

    Splits the last component off as method_kind. The remaining components
    are interpreted as ``module_name . category_path[0] . category_path[1] ...``.

    This parse is namespace-agnostic. It separates the importable module prefix
    from the category path using the first class-like segment (capitalized or
    underscore-prefixed) and leaves semantic Sage validation to later
    instantiation/projection steps. A third-party subtree is therefore eligible
    even when it does not live under ``sage.categories.*``.

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
    cat_start = next(
        (index for index, segment in enumerate(prefix) if _CLASSLIKE_SEGMENT.match(segment)),
        None,
    )
    if cat_start in (None, 0):
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
    _ensure_sage_initialized()
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


def is_sage_category_fullname(fullname: str) -> bool:
    """Return True iff *fullname* resolves to a runtime Sage Category class."""
    module_name, class_path = _split_module_and_class_path(fullname)
    if module_name is None or not class_path:
        return False
    try:
        module = _canonical_import_module(module_name)
        obj: Any = module
        for name in class_path:
            obj = getattr(obj, name)
    except (AttributeError, ImportError, TypeError, ValueError):
        return False

    _ensure_sage_initialized()
    from sage.categories.category import Category

    return isinstance(obj, type) and issubclass(obj, Category)


# ---------------------------------------------------------------------------
# Category instantiation
# ---------------------------------------------------------------------------


def _find_category_owner(
    module: types.ModuleType,
    top_cls: type,
) -> tuple[type, str] | None:
    """Find a Category class in *module* that directly owns *top_cls*.

    Parameterized construction categories such as ``_CartesianProducts`` need
    their owner category as a constructor argument.  This lookup is
    namespace-agnostic: it checks class attribute values by identity, not names.
    """
    _ensure_sage_initialized()
    from sage.categories.category import Category

    for owner_module in _category_owner_search_modules(module):
        for obj in vars(owner_module).values():
            if not (isinstance(obj, type) and issubclass(obj, Category)):
                continue
            if obj is top_cls:
                continue
            attr_name = _owned_category_attribute_name(obj, top_cls)
            if attr_name is not None:
                return obj, attr_name
    return None


def _category_owner_search_modules(module: types.ModuleType) -> tuple[types.ModuleType, ...]:
    modules: list[types.ModuleType] = [module]
    seen = {module.__name__}
    parts = module.__name__.split(".")
    for size in range(len(parts) - 1, 1, -1):
        prefix = ".".join(parts[:size])
        if prefix in seen:
            continue
        try:
            candidate = _load_module_from_source_tree(prefix)
        except Exception:
            _LOG.debug(
                "Sage category owner module discovery failed for %s",
                prefix,
                exc_info=True,
            )
            continue
        if candidate.__name__ in seen:
            continue
        seen.add(candidate.__name__)
        modules.append(candidate)
    return tuple(modules)


def _owned_category_attribute_name(owner_cls: type, top_cls: type) -> str | None:
    for attr_name, attr_val in vars(owner_cls).items():
        if attr_val is top_cls:
            return attr_name
        if _lazy_import_target(attr_val) is top_cls:
            return attr_name
    return None


def _lazy_import_target(value: Any) -> type | None:
    get_object = getattr(value, "_get_object", None)
    if not callable(get_object):
        return None
    try:
        target = get_object()
    except Exception:
        _LOG.debug("Sage lazy construction owner lookup failed", exc_info=True)
        return None
    return target if isinstance(target, type) else None


def _instantiate_category_class(cls: type) -> Any:
    if hasattr(cls, "an_instance"):
        return cls.an_instance()
    return cls()


def instantiate_category_from_source_path(
    module: types.ModuleType,
    category_path: tuple[str, ...],
    representative_args: dict[str, tuple[Any, ...]] | None = None,
) -> Any:
    """Instantiate a Sage category from a source-module and category path.

    When a construction category is a direct class attribute of an owner
    category, instantiates it through Sage's normal construction protocol.
    Otherwise uses ``.an_instance()`` as the preferred instantiation mechanism.

    - Flat: ``category_path = ("Rings",)`` → ``module.Rings.an_instance()``
    - Nested: ``("Objects", "Homsets")`` →
      ``module.Objects.an_instance().Homsets()``
    - Axiom: ``("Monoids", "Finite")`` →
      ``module.Monoids.an_instance().Finite()``
    - Construction: ``("_CartesianProducts",)`` →
      ``_CartesianProducts(owner.an_instance())``

    Args:
        module: The Python module containing the top-level category class.
        category_path: Tuple of attribute names forming the path to the
            category, starting from *module*.

    Returns:
        A Sage category instance.

    Raises:
        AttributeError: If an attribute in the path is missing.
        TypeError: If the category cannot be instantiated without configured
            representative arguments.
        ImportError: If Sage cannot be imported.
    """
    if not category_path:
        raise ValueError("category_path must not be empty")

    # First element: get the category class from the module.
    top_name = category_path[0]
    top_cls = getattr(module, top_name)
    top_fullname = _fullname_of_class(top_cls)

    if representative_args and top_fullname in representative_args:
        cat = top_cls(*representative_args[top_fullname])
    else:
        owner = _find_category_owner(module, top_cls)
        if owner is not None:
            owner_cls, _attr_name = owner
            owner_instance = _instantiate_category_class(owner_cls)
            cat = top_cls(owner_instance)
        else:
            cat = _instantiate_category_class(top_cls)

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


def method_container_direct_bases(
    source_fullname: str,
    representative_args: dict[str, tuple[Any, ...]] | None = None,
) -> list[str]:
    projection = method_container_projection(source_fullname, representative_args)
    if projection is None:
        return []
    return list(projection.static_bases)


def method_container_projection(
    source_fullname: str,
    representative_args: dict[str, tuple[Any, ...]] | None = None,
) -> MethodContainerProjection | None:
    aliases = resolve_method_container_aliases(source_fullname)
    if not aliases:
        return None
    return method_container_projection_for_aliases(
        source_fullname,
        aliases,
        representative_args,
    )


def method_container_projection_for_aliases(
    source_fullname: str,
    aliases: tuple[str, ...] | list[str],
    representative_args: dict[str, tuple[Any, ...]] | None = None,
) -> MethodContainerProjection | None:
    projections: list[MethodContainerProjection] = []
    last_error: Exception | None = None
    for alias in aliases:
        try:
            projections.append(_project_method_container_alias(alias, representative_args))
        except (ParameterizedCategoryError, ProjectionError) as exc:
            last_error = exc

    if not projections:
        if last_error is not None:
            raise last_error
        return None

    dynamic_classes = _dedupe_strings(
        projection.dynamic_class for projection in projections
    )
    dynamic_bases = _dedupe_strings(
        base
        for projection in projections
        for base in projection.dynamic_bases
    )
    unmapped_dynamic_bases = _dedupe_strings(
        base
        for projection in projections
        for base in projection.unmapped_dynamic_bases
    )
    static_bases = _dedupe_strings(
        base
        for projection in projections
        for base in projection.static_bases
    )

    return MethodContainerProjection(
        source_fullname=source_fullname,
        dynamic_class=" | ".join(dynamic_classes),
        dynamic_bases=tuple(dynamic_bases),
        unmapped_dynamic_bases=tuple(unmapped_dynamic_bases),
        static_bases=tuple(static_bases),
    )


def _project_method_container_alias(
    source_fullname: str,
    representative_args: dict[str, tuple[Any, ...]] | None = None,
) -> MethodContainerProjection:
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
        raise ProjectionError(f"{source_fullname!r} is not a canonical method container")

    _ensure_sage_initialized()
    mod = _canonical_import_module(parsed.module_name)
    try:
        cat = instantiate_category_from_source_path(
            mod,
            parsed.category_path,
            representative_args,
        )
    except ParameterizedCategoryError:
        raise
    except TypeError as exc:
        raise ParameterizedCategoryError(
            f"could not instantiate {parsed.module_name}.{'.'.join(parsed.category_path)}"
        ) from exc
    except Exception as exc:
        raise ProjectionError(
            f"could not resolve {parsed.module_name}.{'.'.join(parsed.category_path)}"
        ) from exc

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

    static_bases: list[str] = []
    unmapped_dynamic_bases: list[str] = []
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
            unmapped_dynamic_bases.append(_fullname_of_class(B))
            continue

        source_container = getattr(type(D), parsed.method_kind, None)
        if source_container is None:
            unmapped_dynamic_bases.append(_fullname_of_class(B))
            continue

        fn = _fullname_of_class(source_container)
        if fn not in seen:
            seen.add(fn)
            static_bases.append(fn)

    return MethodContainerProjection(
        source_fullname=source_fullname,
        dynamic_class=_fullname_of_class(dynamic_class),
        dynamic_bases=tuple(_fullname_of_class(base) for base in dynamic_bases),
        unmapped_dynamic_bases=tuple(unmapped_dynamic_bases),
        static_bases=tuple(static_bases),
    )


@lru_cache(maxsize=None)
def resolve_method_container_aliases(source_fullname: str) -> tuple[str, ...]:
    parsed = parse_method_container_fullname(source_fullname)
    if parsed is not None:
        return (source_fullname,)

    module_name, source_class_path = _split_module_and_class_path(source_fullname)
    if module_name is None or not source_class_path:
        return ()

    try:
        _ensure_sage_initialized()
        mod = _canonical_import_module(module_name)
    except Exception:
        return ()
    from sage.categories.category import Category

    aliases: list[str] = []
    for name in dir(mod):
        obj = getattr(mod, name)
        if not (isinstance(obj, type) and issubclass(obj, Category)):
            continue
        owner_fullname = _fullname_of_class(obj)
        _owner_module_name, owner_class_path = _split_module_and_class_path(owner_fullname)
        for kind in _METHOD_KINDS:
            if not hasattr(obj, kind):
                continue
            container_cls = getattr(obj, kind)
            _container_module_name, container_class_path = _split_module_and_class_path(
                _fullname_of_class(container_cls)
            )
            if container_class_path != source_class_path:
                continue
            aliases.append(f"{module_name}.{'.'.join(owner_class_path)}.{kind}")
    return tuple(_dedupe_strings(aliases))


def _canonical_import_module(module_name: str) -> types.ModuleType:
    """Import *module_name*, falling back to importable suffixes if needed.

    Mypy can analyze the same file under a package-prefixed fullname such as
    ``tests.fixtures.sage.categories...`` while the runtime-importable module
    is a suffix such as ``sage.categories...``. Prefer the exact module first:
    third-party namespaces can have importable top-level suffix collisions, and
    choosing a shorter suffix after exact resolution silently points projection
    at the wrong module.
    """
    exact_path = _find_module_path(module_name)
    try:
        return _import_module_candidate(module_name)
    except Exception as exc:
        if exact_path is not None:
            raise
        last_error: Exception | None = exc

    parts = module_name.split(".")
    for start in range(1, len(parts)):
        candidate = ".".join(parts[start:])
        try:
            return _import_module_candidate(candidate)
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise ModuleNotFoundError(module_name)


def _import_module_candidate(module_name: str) -> types.ModuleType:
    try:
        return importlib.import_module(module_name)
    except Exception as import_exc:
        _LOG.debug("Runtime import failed for %s", module_name, exc_info=True)
        try:
            return _load_module_from_source_tree(module_name)
        except Exception as source_exc:
            _LOG.debug("Source-tree import failed for %s", module_name, exc_info=True)
            raise source_exc from import_exc


def _split_module_and_class_path(fullname: str) -> tuple[str | None, tuple[str, ...]]:
    parts = fullname.split(".")
    class_start = next(
        (index for index, segment in enumerate(parts) if _CLASSLIKE_SEGMENT.match(segment)),
        None,
    )
    if class_start in (None, 0):
        return None, ()
    return ".".join(parts[:class_start]), tuple(parts[class_start:])


def _dedupe_strings(items) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _load_module_from_source_tree(module_name: str) -> types.ModuleType:
    if module_name in sys.modules:
        return sys.modules[module_name]

    parts = module_name.split(".")
    for size in range(1, len(parts)):
        prefix = ".".join(parts[:size])
        if prefix in sys.modules:
            continue
        module_path = _find_module_path(prefix)
        if module_path is None:
            raise ModuleNotFoundError(prefix)
        file_path, is_package = module_path
        if size == 1:
            if not is_package:
                raise ModuleNotFoundError(prefix)
            _install_namespace_package(prefix, file_path.parent)
            continue
        if is_package:
            _load_module_file(prefix, file_path, is_package=True)
        else:
            raise ModuleNotFoundError(prefix)

    module_path = _find_module_path(module_name)
    if module_path is None:
        raise ModuleNotFoundError(module_name)
    file_path, is_package = module_path
    return _load_module_file(module_name, file_path, is_package=is_package)


def _find_module_path(module_name: str) -> tuple[Path, bool] | None:
    rel = Path(*module_name.split("."))
    search_roots: list[str] = list(sys.path)
    cwd = str(Path.cwd())
    if cwd not in search_roots:
        search_roots.append(cwd)
    for entry in search_roots:
        if not entry:
            entry = "."
        root = Path(entry)
        package_init = root / rel / "__init__.py"
        if package_init.is_file():
            return package_init, True
        module_file = root / f"{rel}.py"
        if module_file.is_file():
            return module_file, False
    return None


def _install_namespace_package(module_name: str, package_dir: Path) -> types.ModuleType:
    module = types.ModuleType(module_name)
    module.__file__ = str(package_dir)
    module.__package__ = module_name
    module.__path__ = [str(package_dir)]
    spec = importlib.util.spec_from_loader(module_name, loader=None, origin=str(package_dir))
    if spec is not None:
        spec.submodule_search_locations = [str(package_dir)]
        module.__spec__ = spec
    sys.modules[module_name] = module
    return module


def _load_module_file(
    module_name: str,
    file_path: Path,
    *,
    is_package: bool,
) -> types.ModuleType:
    if module_name in sys.modules and getattr(sys.modules[module_name], "__file__", None):
        return sys.modules[module_name]

    if is_package:
        spec = importlib.util.spec_from_file_location(
            module_name,
            file_path,
            submodule_search_locations=[str(file_path.parent)],
        )
    else:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(module_name)

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        with _compat_abstractmethod_signature():
            spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


@contextmanager
def _compat_abstractmethod_signature():
    import abc

    original = abc.abstractmethod

    def compat(func=None, /, **kwargs):
        kwargs.pop("optional", None)
        if kwargs:
            unexpected = ", ".join(sorted(kwargs))
            raise TypeError(f"abstractmethod() got unexpected keyword arguments: {unexpected}")
        if func is None:
            def decorate(inner):
                return original(inner)
            return decorate
        return original(func)

    abc.abstractmethod = compat
    try:
        yield
    finally:
        abc.abstractmethod = original


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
    _ensure_sage_initialized()
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
    _ensure_sage_initialized()
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
        projection = method_container_projection(source_fullname)
    except Exception as exc:
        return f"{source_fullname}: error during projection — {exc}"
    if projection is None:
        return f"{source_fullname}: no projection"

    lines = [
        f"source: {projection.source_fullname}",
        f"dynamic class: {projection.dynamic_class}",
        "dynamic bases:",
    ]
    if not projection.dynamic_bases:
        lines.append("  (none)")
    else:
        lines.extend(f"  {base}" for base in projection.dynamic_bases)
    lines.append("injected static bases:")
    if not projection.static_bases:
        lines.append("  (none)")
    else:
        lines.extend(f"  {base}" for base in projection.static_bases)

    return "\n".join(lines)
