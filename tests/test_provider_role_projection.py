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


def _runtime_class(category: object, attr: str) -> type[object]:
    runtime_class = getattr(category, attr)
    assert isinstance(runtime_class, type)
    return runtime_class


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

    category_element_class = _runtime_class(category, "element_class")
    runtime_to_provider = {
        category_element_class: BottomCategory.ElementMethods,
        _runtime_class(RightCategory.an_instance(), "element_class"): (
            RightCategory.ElementMethods
        ),
        _runtime_class(LeftCategory.an_instance(), "element_class"): (
            LeftCategory.ElementMethods
        ),
        _runtime_class(TopCategory.an_instance(), "element_class"): (
            TopCategory.ElementMethods
        ),
    }
    projected_runtime_bases = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category_element_class.__bases__
    )
    projected_runtime_mro = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category_element_class.__mro__
        if runtime_class in runtime_to_provider
    )
    unprojected_runtime_mro = tuple(
        runtime_class
        for runtime_class in category_element_class.__mro__
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

    category_subcategory_class = _runtime_class(category, "subcategory_class")
    runtime_to_provider = {
        category_subcategory_class: BottomCategory.SubcategoryMethods,
        _runtime_class(RightCategory.an_instance(), "subcategory_class"): (
            RightCategory.SubcategoryMethods
        ),
        _runtime_class(LeftCategory.an_instance(), "subcategory_class"): (
            LeftCategory.SubcategoryMethods
        ),
        _runtime_class(TopCategory.an_instance(), "subcategory_class"): (
            TopCategory.SubcategoryMethods
        ),
    }
    projected_runtime_bases = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category_subcategory_class.__bases__
    )
    projected_runtime_mro = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category_subcategory_class.__mro__
        if runtime_class in runtime_to_provider
    )
    unprojected_runtime_mro = tuple(
        runtime_class
        for runtime_class in category_subcategory_class.__mro__
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


def test_diamond_morphism_projection_matches_sage_runtime_mro() -> None:
    projections = provider_projections_for_categories(
        ("tests.fixtures.invariant_core.provider_roles.diamond.BottomCategory",),
        roles=("morphism",),
    )

    category = BottomCategory.an_instance()
    morphism_provider = (
        "tests.fixtures.invariant_core.provider_roles.diamond.BottomCategory.MorphismMethods"
    )
    projection = projections[morphism_provider]

    category_morphism_class = _runtime_class(category, "morphism_class")
    runtime_to_provider = {
        category_morphism_class: BottomCategory.MorphismMethods,
        _runtime_class(RightCategory.an_instance(), "morphism_class"): (
            RightCategory.MorphismMethods
        ),
        _runtime_class(LeftCategory.an_instance(), "morphism_class"): (
            LeftCategory.MorphismMethods
        ),
        _runtime_class(TopCategory.an_instance(), "morphism_class"): (
            TopCategory.MorphismMethods
        ),
    }
    projected_runtime_bases = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category_morphism_class.__bases__
    )
    projected_runtime_mro = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category_morphism_class.__mro__
        if runtime_class in runtime_to_provider
    )
    unprojected_runtime_mro = tuple(
        runtime_class
        for runtime_class in category_morphism_class.__mro__
        if runtime_class not in runtime_to_provider
    )

    assert projection.provider == morphism_provider
    assert projection.role == "morphism"
    assert projection.runtime_bases == (
        "tests.fixtures.invariant_core.provider_roles.diamond.RightCategory.morphism_class",
        "tests.fixtures.invariant_core.provider_roles.diamond.LeftCategory.morphism_class",
    )
    assert projection.runtime_mro == (
        "tests.fixtures.invariant_core.provider_roles.diamond.BottomCategory.morphism_class",
        "tests.fixtures.invariant_core.provider_roles.diamond.RightCategory.morphism_class",
        "tests.fixtures.invariant_core.provider_roles.diamond.LeftCategory.morphism_class",
        "tests.fixtures.invariant_core.provider_roles.diamond.TopCategory.morphism_class",
        "builtins.object",
    )
    assert unprojected_runtime_mro == (object,)
    assert projection.provider_bases == projected_runtime_bases
    assert projection.provider_mro == projected_runtime_mro
    assert projection.provider_bases == (
        "tests.fixtures.invariant_core.provider_roles.diamond.RightCategory.MorphismMethods",
        "tests.fixtures.invariant_core.provider_roles.diamond.LeftCategory.MorphismMethods",
    )
    assert projection.provider_mro == (
        "tests.fixtures.invariant_core.provider_roles.diamond.BottomCategory.MorphismMethods",
        "tests.fixtures.invariant_core.provider_roles.diamond.RightCategory.MorphismMethods",
        "tests.fixtures.invariant_core.provider_roles.diamond.LeftCategory.MorphismMethods",
        "tests.fixtures.invariant_core.provider_roles.diamond.TopCategory.MorphismMethods",
    )
