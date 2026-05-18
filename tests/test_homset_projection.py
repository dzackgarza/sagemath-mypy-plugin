from __future__ import annotations

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.homsets import Homsets  # type: ignore[import-untyped]
from sage.categories.objects import Objects  # type: ignore[import-untyped]
from sage.categories.sets_cat import Sets  # type: ignore[import-untyped]

from sage_mypy_category_plugin.oracle import provider_projections_for_categories
from tests.fixtures.invariant_core.provider_roles.homsets import (
    BottomCategory,
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
