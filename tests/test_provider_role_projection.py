from __future__ import annotations

from tests.fixtures.invariant_core.provider_roles.diamond import (
    BottomCategory,
    LeftCategory,
    RightCategory,
    TopCategory,
)
from sage_mypy_category_plugin.oracle import provider_projections_for_categories


def _class_fullname(cls: type[object]) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def test_diamond_element_projection_matches_sage_runtime_mro() -> None:
    projections = provider_projections_for_categories(
        ("tests.fixtures.invariant_core.provider_roles.diamond.BottomCategory",),
        roles=("element",),
    )

    category = BottomCategory.an_instance()
    element_provider = (
        "tests.fixtures.invariant_core.provider_roles.diamond.BottomCategory.ElementMethods"
    )
    projection = projections[element_provider]

    runtime_to_provider = {
        category.element_class: BottomCategory.ElementMethods,
        RightCategory.an_instance().element_class: RightCategory.ElementMethods,
        LeftCategory.an_instance().element_class: LeftCategory.ElementMethods,
        TopCategory.an_instance().element_class: TopCategory.ElementMethods,
    }
    projected_runtime_bases = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category.element_class.__bases__
    )
    projected_runtime_mro = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category.element_class.__mro__
        if runtime_class in runtime_to_provider
    )
    unprojected_runtime_mro = tuple(
        runtime_class
        for runtime_class in category.element_class.__mro__
        if runtime_class not in runtime_to_provider
    )

    assert projection.provider == element_provider
    assert projection.role == "element"
    assert projection.runtime_bases == (
        "tests.fixtures.invariant_core.provider_roles.diamond.RightCategory.element_class",
        "tests.fixtures.invariant_core.provider_roles.diamond.LeftCategory.element_class",
    )
    assert projection.runtime_mro == (
        "tests.fixtures.invariant_core.provider_roles.diamond.BottomCategory.element_class",
        "tests.fixtures.invariant_core.provider_roles.diamond.RightCategory.element_class",
        "tests.fixtures.invariant_core.provider_roles.diamond.LeftCategory.element_class",
        "tests.fixtures.invariant_core.provider_roles.diamond.TopCategory.element_class",
        "builtins.object",
    )
    assert unprojected_runtime_mro == (object,)
    assert projection.provider_bases == projected_runtime_bases
    assert projection.provider_mro == projected_runtime_mro
    assert projection.provider_bases == (
        "tests.fixtures.invariant_core.provider_roles.diamond.RightCategory.ElementMethods",
        "tests.fixtures.invariant_core.provider_roles.diamond.LeftCategory.ElementMethods",
    )
    assert projection.provider_mro == (
        "tests.fixtures.invariant_core.provider_roles.diamond.BottomCategory.ElementMethods",
        "tests.fixtures.invariant_core.provider_roles.diamond.RightCategory.ElementMethods",
        "tests.fixtures.invariant_core.provider_roles.diamond.LeftCategory.ElementMethods",
        "tests.fixtures.invariant_core.provider_roles.diamond.TopCategory.ElementMethods",
    )


def test_diamond_subcategory_projection_matches_sage_runtime_mro() -> None:
    projections = provider_projections_for_categories(
        ("tests.fixtures.invariant_core.provider_roles.diamond.BottomCategory",),
        roles=("subcategory",),
    )

    category = BottomCategory.an_instance()
    subcategory_provider = (
        "tests.fixtures.invariant_core.provider_roles.diamond.BottomCategory.SubcategoryMethods"
    )
    projection = projections[subcategory_provider]

    runtime_to_provider = {
        category.subcategory_class: BottomCategory.SubcategoryMethods,
        RightCategory.an_instance().subcategory_class: RightCategory.SubcategoryMethods,
        LeftCategory.an_instance().subcategory_class: LeftCategory.SubcategoryMethods,
        TopCategory.an_instance().subcategory_class: TopCategory.SubcategoryMethods,
    }
    projected_runtime_bases = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category.subcategory_class.__bases__
    )
    projected_runtime_mro = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category.subcategory_class.__mro__
        if runtime_class in runtime_to_provider
    )
    unprojected_runtime_mro = tuple(
        runtime_class
        for runtime_class in category.subcategory_class.__mro__
        if runtime_class not in runtime_to_provider
    )

    assert projection.provider == subcategory_provider
    assert projection.role == "subcategory"
    assert projection.runtime_bases == (
        "tests.fixtures.invariant_core.provider_roles.diamond.RightCategory.subcategory_class",
        "tests.fixtures.invariant_core.provider_roles.diamond.LeftCategory.subcategory_class",
    )
    assert projection.runtime_mro == (
        "tests.fixtures.invariant_core.provider_roles.diamond.BottomCategory.subcategory_class",
        "tests.fixtures.invariant_core.provider_roles.diamond.RightCategory.subcategory_class",
        "tests.fixtures.invariant_core.provider_roles.diamond.LeftCategory.subcategory_class",
        "tests.fixtures.invariant_core.provider_roles.diamond.TopCategory.subcategory_class",
        "builtins.object",
    )
    assert unprojected_runtime_mro == (object,)
    assert projection.provider_bases == projected_runtime_bases
    assert projection.provider_mro == projected_runtime_mro
    assert projection.provider_bases == (
        "tests.fixtures.invariant_core.provider_roles.diamond.RightCategory.SubcategoryMethods",
        "tests.fixtures.invariant_core.provider_roles.diamond.LeftCategory.SubcategoryMethods",
    )
    assert projection.provider_mro == (
        "tests.fixtures.invariant_core.provider_roles.diamond.BottomCategory.SubcategoryMethods",
        "tests.fixtures.invariant_core.provider_roles.diamond.RightCategory.SubcategoryMethods",
        "tests.fixtures.invariant_core.provider_roles.diamond.LeftCategory.SubcategoryMethods",
        "tests.fixtures.invariant_core.provider_roles.diamond.TopCategory.SubcategoryMethods",
    )
