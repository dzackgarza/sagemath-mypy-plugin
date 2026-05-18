from __future__ import annotations

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.finite_sets import FiniteSets  # type: ignore[import-untyped]
from sage.categories.objects import Objects  # type: ignore[import-untyped]
from sage.categories.sets_cat import Sets  # type: ignore[import-untyped]

from sage_mypy_category_plugin.oracle import provider_projections_for_categories
from tests.fixtures.invariant_core.axioms import AxiomRootCategory

AXIOM_MODULE = "tests.fixtures.invariant_core.axioms"
NESTED_AXIOM_CATEGORY = f"{AXIOM_MODULE}.AxiomRootCategory.Finite"
NESTED_AXIOM_PROVIDER = f"{NESTED_AXIOM_CATEGORY}.ParentMethods"
ROOT_PROVIDER = f"{AXIOM_MODULE}.AxiomRootCategory.ParentMethods"


def _class_fullname(cls: type[object]) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def test_nested_axiom_projection_matches_sage_runtime_mro() -> None:
    projections = provider_projections_for_categories(
        (NESTED_AXIOM_CATEGORY,),
        roles=("parent",),
    )

    category = AxiomRootCategory.an_instance().Finite()
    projection = projections[NESTED_AXIOM_PROVIDER]
    runtime_to_provider = {
        category.parent_class: AxiomRootCategory.Finite.ParentMethods,
        FiniteSets().parent_class: FiniteSets.ParentMethods,
        AxiomRootCategory.an_instance().parent_class: AxiomRootCategory.ParentMethods,
        Sets().parent_class: Sets.ParentMethods,
        Objects().parent_class: Objects.ParentMethods,
    }
    projected_runtime_bases = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category.parent_class.__bases__
        if runtime_class in runtime_to_provider
    )
    projected_runtime_mro = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category.parent_class.__mro__
        if runtime_class in runtime_to_provider
    )
    unprojected_runtime_mro = tuple(
        _class_fullname(runtime_class)
        for runtime_class in category.parent_class.__mro__
        if runtime_class not in runtime_to_provider and runtime_class is not object
    )

    assert projection.provider == NESTED_AXIOM_PROVIDER
    assert projection.role == "parent"
    assert projection.runtime_bases == tuple(
        _class_fullname(runtime_class) for runtime_class in category.parent_class.__bases__
    )
    assert projection.runtime_mro == tuple(
        _class_fullname(runtime_class) for runtime_class in category.parent_class.__mro__
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
