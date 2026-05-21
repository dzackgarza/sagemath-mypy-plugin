from __future__ import annotations

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.homsets import Homsets  # type: ignore[import-untyped]
from sage.categories.objects import Objects  # type: ignore[import-untyped]
from sage.categories.sets_cat import Sets  # type: ignore[import-untyped]

from sage_mypy_category_plugin.oracle import provider_projections_for_categories
from sage_mypy_category_plugin.oracle import unsupported_provider_traces
from tests.fixtures.invariant_core.provider_roles.homsets import (
    BottomCategory,
    LocalFiniteEndHomCategory,
    RefinedSharedHomsetProviderCategory,
    SharedHomsetProviderCategory,
    SharedHomsetParentMethods,
    SharedStandaloneHomCategory,
    TopCategory,
)


def _class_fullname(cls: type[object]) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def test_homset_parent_projection_matches_sage_runtime_mro() -> None:
    projections = provider_projections_for_categories(
        ("tests.fixtures.invariant_core.provider_roles.homsets.BottomCategory",),
        roles=("homset_parent",),
    )

    category = BottomCategory.an_instance()
    homsets = category.Homsets()
    provider = (
        "tests.fixtures.invariant_core.provider_roles.homsets."
        "BottomCategory.Homsets.ParentMethods"
    )
    projection = projections[provider]
    runtime_to_provider = {
        homsets.parent_class: BottomCategory.Homsets.ParentMethods,
        TopCategory.an_instance().Homsets().parent_class: (
            TopCategory.Homsets.ParentMethods
        ),
        Homsets().parent_class: Homsets.ParentMethods,
        Sets().parent_class: Sets.ParentMethods,
        Objects().parent_class: Objects.ParentMethods,
    }
    projected_runtime_bases = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in homsets.parent_class.__bases__
        if runtime_class in runtime_to_provider
    )
    projected_runtime_mro = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in homsets.parent_class.__mro__
        if runtime_class in runtime_to_provider
    )
    unprojected_runtime_mro = tuple(
        _class_fullname(runtime_class)
        for runtime_class in homsets.parent_class.__mro__
        if runtime_class not in runtime_to_provider and runtime_class is not object
    )

    assert projection.provider == provider
    assert projection.role == "homset_parent"
    assert projection.runtime_bases == tuple(
        _class_fullname(runtime_class)
        for runtime_class in homsets.parent_class.__bases__
    )
    assert projection.runtime_mro == tuple(
        _class_fullname(runtime_class)
        for runtime_class in homsets.parent_class.__mro__
    )
    assert projection.provider_bases == projected_runtime_bases
    assert projection.provider_mro == projected_runtime_mro
    assert projection.unprojected_runtime_mro == unprojected_runtime_mro
    assert projection.unprojected_runtime_mro == (
        "sage.categories.sets_with_partial_maps.SetsWithPartialMaps.parent_class",
    )
    assert projection.provider_bases == (
        "tests.fixtures.invariant_core.provider_roles.homsets."
        "TopCategory.Homsets.ParentMethods",
    )
    assert projection.provider_mro == (
        "tests.fixtures.invariant_core.provider_roles.homsets."
        "BottomCategory.Homsets.ParentMethods",
        "tests.fixtures.invariant_core.provider_roles.homsets."
        "TopCategory.Homsets.ParentMethods",
        "sage.categories.homsets.Homsets.ParentMethods",
        "sage.categories.sets_cat.Sets.ParentMethods",
        "sage.categories.objects.Objects.ParentMethods",
    )


def test_homset_element_projection_matches_sage_runtime_mro() -> None:
    projections = provider_projections_for_categories(
        ("tests.fixtures.invariant_core.provider_roles.homsets.BottomCategory",),
        roles=("homset_element",),
    )

    category = BottomCategory.an_instance()
    homsets = category.Homsets()
    provider = (
        "tests.fixtures.invariant_core.provider_roles.homsets."
        "BottomCategory.Homsets.ElementMethods"
    )
    projection = projections[provider]
    runtime_to_provider = {
        homsets.element_class: BottomCategory.Homsets.ElementMethods,
        TopCategory.an_instance().Homsets().element_class: (
            TopCategory.Homsets.ElementMethods
        ),
        Sets().element_class: Sets.ElementMethods,
    }
    projected_runtime_bases = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in homsets.element_class.__bases__
        if runtime_class in runtime_to_provider
    )
    projected_runtime_mro = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in homsets.element_class.__mro__
        if runtime_class in runtime_to_provider
    )
    unprojected_runtime_mro = tuple(
        _class_fullname(runtime_class)
        for runtime_class in homsets.element_class.__mro__
        if runtime_class not in runtime_to_provider and runtime_class is not object
    )

    assert projection.provider == provider
    assert projection.role == "homset_element"
    assert projection.runtime_bases == tuple(
        _class_fullname(runtime_class)
        for runtime_class in homsets.element_class.__bases__
    )
    assert projection.runtime_mro == tuple(
        _class_fullname(runtime_class)
        for runtime_class in homsets.element_class.__mro__
    )
    assert projection.provider_bases == projected_runtime_bases
    assert projection.provider_mro == projected_runtime_mro
    assert projection.unprojected_runtime_mro == unprojected_runtime_mro
    assert projection.unprojected_runtime_mro == (
        "sage.categories.homsets.Homsets.element_class",
        "sage.categories.sets_with_partial_maps.SetsWithPartialMaps.element_class",
        "sage.categories.objects.Objects.element_class",
    )
    assert projection.provider_bases == (
        "tests.fixtures.invariant_core.provider_roles.homsets."
        "TopCategory.Homsets.ElementMethods",
    )
    assert projection.provider_mro == (
        "tests.fixtures.invariant_core.provider_roles.homsets."
        "BottomCategory.Homsets.ElementMethods",
        "tests.fixtures.invariant_core.provider_roles.homsets."
        "TopCategory.Homsets.ElementMethods",
        "sage.categories.sets_cat.Sets.ElementMethods",
    )


def test_homset_projection_classifies_shared_provider_with_distinct_runtime_mros() -> None:
    category = SharedHomsetProviderCategory
    provider = _class_fullname(SharedHomsetParentMethods)

    projections = provider_projections_for_categories(
        (f"{category.__module__}.{category.__qualname__}",),
        roles=("homset_parent",),
    )
    unsupported_provider = {
        trace.provider: trace for trace in unsupported_provider_traces()
    }[provider]
    standalone_runtime_class = SharedStandaloneHomCategory().parent_class
    homset_runtime_class = category.an_instance().Homsets().parent_class

    assert provider not in projections
    assert unsupported_provider.role == "homset_parent"
    assert unsupported_provider.reason == "ambiguous_runtime_mro"
    assert unsupported_provider.runtime_classes == (
        _class_fullname(standalone_runtime_class),
        _class_fullname(homset_runtime_class),
    )
    assert unsupported_provider.runtime_mros == (
        tuple(
            _class_fullname(runtime_class)
            for runtime_class in standalone_runtime_class.__mro__
        ),
        tuple(
            _class_fullname(runtime_class)
            for runtime_class in homset_runtime_class.__mro__
        ),
    )


def test_dependent_homset_projection_keeps_unsupported_shared_provider_base() -> None:
    projections = provider_projections_for_categories(
        (
            "tests.fixtures.invariant_core.provider_roles.homsets."
            "RefinedSharedHomsetProviderCategory",
        ),
        roles=("homset_parent",),
    )

    refined_provider = (
        "tests.fixtures.invariant_core.provider_roles.homsets."
        "RefinedSharedHomsetProviderCategory.Homsets.ParentMethods"
    )
    shared_provider = _class_fullname(SharedHomsetParentMethods)
    projection = projections[refined_provider]
    unsupported_provider = {
        trace.provider: trace for trace in unsupported_provider_traces()
    }[shared_provider]
    runtime_class = (
        RefinedSharedHomsetProviderCategory.an_instance().Homsets().parent_class
    )

    assert unsupported_provider.reason == "ambiguous_runtime_mro"
    assert shared_provider not in projections
    assert projection.runtime_bases == tuple(
        _class_fullname(runtime_base) for runtime_base in runtime_class.__bases__
    )
    assert projection.provider_bases == (shared_provider,)
    assert projection.provider_mro == (
        refined_provider,
        shared_provider,
        "sage.categories.objects.Objects.ParentMethods",
    )


def test_axiom_homset_projection_closes_runtime_provider_registry() -> None:
    projections = provider_projections_for_categories(
        (
            "tests.fixtures.invariant_core.provider_roles.homsets."
            "LocalFiniteEndHomCategory",
        ),
        roles=("homset_parent",),
    )

    finite_provider = _class_fullname(LocalFiniteEndHomCategory.ParentMethods)
    projection = projections[finite_provider]

    assert projection.provider == finite_provider
    assert projection.role == "homset_parent"
    assert projection.runtime_class == (
        "tests.fixtures.invariant_core.provider_roles.homsets."
        "LocalFiniteEndHomCategory.parent_class"
    )
    assert projection.provider_mro == (
        finite_provider,
        "sage.categories.finite_monoids.FiniteMonoids.ParentMethods",
        "tests.fixtures.invariant_core.provider_roles.homsets."
        "LocalEndHomCategory.ParentMethods",
        "sage.categories.homsets.Homsets.Endset.ParentMethods",
        "sage.categories.monoids.Monoids.ParentMethods",
        "sage.categories.finite_semigroups.FiniteSemigroups.ParentMethods",
        "sage.categories.semigroups.Semigroups.ParentMethods",
        "sage.categories.magmas.Magmas.Unital.ParentMethods",
        "sage.categories.magmas.Magmas.ParentMethods",
        "sage.categories.finite_sets.FiniteSets.ParentMethods",
        "tests.fixtures.invariant_core.provider_roles.homsets."
        "StandaloneHomCategory.ParentMethods",
        "sage.categories.homsets.Homsets.ParentMethods",
        "sage.categories.sets_cat.Sets.ParentMethods",
        "sage.categories.objects.Objects.ParentMethods",
    )
