from __future__ import annotations

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.finite_sets import FiniteSets  # type: ignore[import-untyped]
from sage.categories.objects import Objects  # type: ignore[import-untyped]
from sage.categories.sets_cat import Sets  # type: ignore[import-untyped]

from sage_mypy_category_plugin.oracle import provider_projections_for_categories
from tests.fixtures.invariant_core.axioms import AxiomRootCategory
from tests.fixtures.invariant_core.linked_axiom_finite import LinkedFiniteAxiomCategory
from tests.fixtures.invariant_core.linked_axiom_root import LinkedAxiomRootCategory

AXIOM_MODULE = "tests.fixtures.invariant_core.axioms"
NESTED_AXIOM_CATEGORY = f"{AXIOM_MODULE}.AxiomRootCategory.Finite"
NESTED_AXIOM_PROVIDER = f"{NESTED_AXIOM_CATEGORY}.ParentMethods"
ROOT_PROVIDER = f"{AXIOM_MODULE}.AxiomRootCategory.ParentMethods"
LINKED_AXIOM_ROOT_MODULE = "tests.fixtures.invariant_core.linked_axiom_root"
LINKED_AXIOM_FINITE_MODULE = "tests.fixtures.invariant_core.linked_axiom_finite"
LINKED_AXIOM_CATEGORY = (
    f"{LINKED_AXIOM_ROOT_MODULE}.LinkedAxiomRootCategory.Finite"
)
LINKED_AXIOM_PROVIDER = (
    f"{LINKED_AXIOM_FINITE_MODULE}.LinkedFiniteAxiomCategory.ParentMethods"
)
LINKED_ROOT_PROVIDER = (
    f"{LINKED_AXIOM_ROOT_MODULE}.LinkedAxiomRootCategory.ParentMethods"
)


def _class_fullname(cls: type[object]) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def _runtime_class(owner: object, attr: str) -> type[object]:
    runtime_class = getattr(owner, attr)
    assert isinstance(runtime_class, type)
    return runtime_class


def _runtime_category(owner: object, attr: str) -> object:
    factory = getattr(owner, attr)
    assert callable(factory)
    return factory()


def test_nested_axiom_projection_matches_sage_runtime_mro() -> None:
    projections = provider_projections_for_categories(
        (NESTED_AXIOM_CATEGORY,),
        roles=("parent",),
    )

    category = _runtime_category(AxiomRootCategory.an_instance(), "Finite")
    category_parent_class = _runtime_class(category, "parent_class")
    projection = projections[NESTED_AXIOM_PROVIDER]
    runtime_to_provider = {
        category_parent_class: AxiomRootCategory.Finite.ParentMethods,
        _runtime_class(FiniteSets(), "parent_class"): FiniteSets.ParentMethods,
        _runtime_class(AxiomRootCategory.an_instance(), "parent_class"): (
            AxiomRootCategory.ParentMethods
        ),
        _runtime_class(Sets(), "parent_class"): Sets.ParentMethods,
        _runtime_class(Objects(), "parent_class"): Objects.ParentMethods,
    }
    projected_runtime_bases = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category_parent_class.__bases__
        if runtime_class in runtime_to_provider
    )
    projected_runtime_mro = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category_parent_class.__mro__
        if runtime_class in runtime_to_provider
    )
    unprojected_runtime_mro = tuple(
        _class_fullname(runtime_class)
        for runtime_class in category_parent_class.__mro__
        if runtime_class not in runtime_to_provider and runtime_class is not object
    )

    assert projection.provider == NESTED_AXIOM_PROVIDER
    assert projection.role == "parent"
    assert projection.runtime_bases == tuple(
        _class_fullname(runtime_class)
        for runtime_class in category_parent_class.__bases__
    )
    assert projection.runtime_mro == tuple(
        _class_fullname(runtime_class)
        for runtime_class in category_parent_class.__mro__
    )
    assert projection.provider_bases == projected_runtime_bases
    assert projection.provider_mro == projected_runtime_mro
    assert projection.unprojected_runtime_mro == unprojected_runtime_mro
    assert projection.provider_bases == (
        "sage.categories.finite_sets.FiniteSets.ParentMethods",
        ROOT_PROVIDER,
    )
    assert projection.provider_mro == (
        NESTED_AXIOM_PROVIDER,
        "sage.categories.finite_sets.FiniteSets.ParentMethods",
        ROOT_PROVIDER,
        "sage.categories.sets_cat.Sets.ParentMethods",
        "sage.categories.objects.Objects.ParentMethods",
    )


def test_linked_axiom_projection_matches_sage_runtime_mro() -> None:
    projections = provider_projections_for_categories(
        (LINKED_AXIOM_CATEGORY,),
        roles=("parent",),
    )

    category = _runtime_category(LinkedAxiomRootCategory.an_instance(), "Finite")
    category_parent_class = _runtime_class(category, "parent_class")
    projection = projections[LINKED_AXIOM_PROVIDER]
    runtime_to_provider = {
        category_parent_class: LinkedFiniteAxiomCategory.ParentMethods,
        _runtime_class(FiniteSets(), "parent_class"): FiniteSets.ParentMethods,
        _runtime_class(LinkedAxiomRootCategory.an_instance(), "parent_class"): (
            LinkedAxiomRootCategory.ParentMethods
        ),
        _runtime_class(Sets(), "parent_class"): Sets.ParentMethods,
        _runtime_class(Objects(), "parent_class"): Objects.ParentMethods,
    }
    projected_runtime_bases = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category_parent_class.__bases__
        if runtime_class in runtime_to_provider
    )
    projected_runtime_mro = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category_parent_class.__mro__
        if runtime_class in runtime_to_provider
    )
    unprojected_runtime_mro = tuple(
        _class_fullname(runtime_class)
        for runtime_class in category_parent_class.__mro__
        if runtime_class not in runtime_to_provider and runtime_class is not object
    )

    assert _runtime_class(LinkedAxiomRootCategory, "Finite") is LinkedFiniteAxiomCategory
    assert projection.provider == LINKED_AXIOM_PROVIDER
    assert projection.role == "parent"
    assert projection.runtime_bases == tuple(
        _class_fullname(runtime_class)
        for runtime_class in category_parent_class.__bases__
    )
    assert projection.runtime_mro == tuple(
        _class_fullname(runtime_class)
        for runtime_class in category_parent_class.__mro__
    )
    assert projection.provider_bases == projected_runtime_bases
    assert projection.provider_mro == projected_runtime_mro
    assert projection.unprojected_runtime_mro == unprojected_runtime_mro
    assert projection.provider_bases == (
        "sage.categories.finite_sets.FiniteSets.ParentMethods",
        LINKED_ROOT_PROVIDER,
    )
    assert projection.provider_mro == (
        LINKED_AXIOM_PROVIDER,
        "sage.categories.finite_sets.FiniteSets.ParentMethods",
        LINKED_ROOT_PROVIDER,
        "sage.categories.sets_cat.Sets.ParentMethods",
        "sage.categories.objects.Objects.ParentMethods",
    )
