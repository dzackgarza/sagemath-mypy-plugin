from __future__ import annotations

import pytest

from sage_mypy_category_plugin.oracle import RoleProjection
from sage_mypy_category_plugin.oracle import provider_projections_for_categories
from sage_mypy_category_plugin.oracle import named_class_traces
from sage_mypy_category_plugin.oracle import _provider_fullname_from_runtime_class_or_none
from tests.fixtures.invariant_core.diamond_runtime import (
    BottomCategory,
    LeftCategory,
    RightCategory,
    TopCategory,
)
from tests.fixtures.invariant_core.functorial.cartesian_products import (
    CartesianProductsCategory,
)
from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


def _class_fullname(cls: type[object]) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


class RuntimeProviderResolutionFixtures:
    class WithProvider:
        class ParentMethods:
            pass

        class parent_class:
            pass

    class WithoutProvider:
        class parent_class:
            pass

    class BrokenProvider:
        ParentMethods = object()

        class parent_class:
            pass


def test_runtime_provider_resolution_rejects_broken_provider_attribute() -> None:
    role_projection = RoleProjection(
        runtime_attr="parent_class",
        provider_attr="ParentMethods",
    )

    assert _provider_fullname_from_runtime_class_or_none(
        RuntimeProviderResolutionFixtures.WithProvider.parent_class,
        role_projection,
    ) == (
        "tests.test_oracle_projection.RuntimeProviderResolutionFixtures."
        "WithProvider.ParentMethods"
    )
    assert _provider_fullname_from_runtime_class_or_none(
        RuntimeProviderResolutionFixtures.WithoutProvider.parent_class,
        role_projection,
    ) is None
    with pytest.raises(AssertionError):
        _provider_fullname_from_runtime_class_or_none(
            RuntimeProviderResolutionFixtures.BrokenProvider.parent_class,
            role_projection,
        )


def test_diamond_parent_projection_matches_sage_runtime_mro() -> None:
    assert BottomCategory.__bases__ == (LocalCategoryBase,)

    projections = provider_projections_for_categories(
        ("tests.fixtures.invariant_core.diamond_runtime.BottomCategory",),
        roles=("parent",),
    )

    provider = "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods"
    projection = projections[provider]
    category = BottomCategory.an_instance()
    runtime_to_provider = {
        category.parent_class: BottomCategory.ParentMethods,
        RightCategory.an_instance().parent_class: RightCategory.ParentMethods,
        LeftCategory.an_instance().parent_class: LeftCategory.ParentMethods,
        TopCategory.an_instance().parent_class: TopCategory.ParentMethods,
    }
    projected_runtime_bases = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category.parent_class.__bases__
    )
    projected_runtime_mro = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category.parent_class.__mro__
        if runtime_class in runtime_to_provider
    )
    unprojected_mro = tuple(
        runtime_class
        for runtime_class in category.parent_class.__mro__
        if runtime_class not in runtime_to_provider
    )

    assert projection.provider == provider
    assert projection.role == "parent"
    assert projection.runtime_bases == tuple(
        _class_fullname(runtime_class) for runtime_class in category.parent_class.__bases__
    )
    assert projection.runtime_mro == tuple(
        _class_fullname(runtime_class) for runtime_class in category.parent_class.__mro__
    )
    assert unprojected_mro == (object,)
    assert projection.provider_bases == projected_runtime_bases
    assert projection.provider_mro == projected_runtime_mro
    assert projection.provider_bases == (
        "tests.fixtures.invariant_core.diamond_runtime.RightCategory.ParentMethods",
        "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.ParentMethods",
    )
    assert projection.provider_mro == (
        "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods",
        "tests.fixtures.invariant_core.diamond_runtime.RightCategory.ParentMethods",
        "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.ParentMethods",
        "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
    )


def test_root_parent_projection_keeps_only_provider_classes() -> None:
    projections = provider_projections_for_categories(
        ("tests.fixtures.invariant_core.diamond_runtime.TopCategory",),
        roles=("parent",),
    )

    provider = "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods"
    projection = projections[provider]
    category = TopCategory.an_instance()

    assert category.parent_class.__bases__ == (object,)
    assert projection.provider == provider
    assert projection.runtime_bases == ("builtins.object",)
    assert projection.provider_bases == ()
    assert projection.provider_mro == (
        "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
    )


def test_tracing_observes_make_named_class() -> None:
    provider = "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods"

    projections = provider_projections_for_categories(
        ("tests.fixtures.invariant_core.diamond_runtime.BottomCategory",),
        roles=("parent",),
    )
    projection = projections[provider]
    traces = named_class_traces()
    trace = next(trace for trace in traces if trace.provider == provider)

    assert projection.runtime_class == trace.runtime_class
    assert projection.runtime_bases == trace.runtime_bases
    assert projection.runtime_mro == trace.runtime_mro
    assert projection.provider_bases == (
        "tests.fixtures.invariant_core.diamond_runtime.RightCategory.ParentMethods",
        "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.ParentMethods",
    )
    assert projection.provider_mro == (
        "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods",
        "tests.fixtures.invariant_core.diamond_runtime.RightCategory.ParentMethods",
        "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.ParentMethods",
        "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
    )
    assert trace.trace_source == "Category._make_named_class"


def test_category_specs_like_parent_projection_uses_local_wrapper_alias() -> None:
    from tests.fixtures.invariant_core.category_specs_like.cat import (
        Category,
        Category_singleton,
    )
    from tests.fixtures.invariant_core.category_specs_like.rings import (
        Rings,
        _RingObjectMethods,
    )
    from tests.fixtures.invariant_core.category_specs_like.rings.subcategories.commutative import (
        _CommutativeRings,
    )

    assert Rings.__bases__ == (Category_singleton,)
    assert _CommutativeRings.__bases__ == (Category,)
    assert Rings.ParentMethods is _RingObjectMethods

    projections = provider_projections_for_categories(
        (
            "tests.fixtures.invariant_core.category_specs_like.rings.Rings",
            "tests.fixtures.invariant_core.category_specs_like.rings.subcategories.commutative._CommutativeRings",
        ),
        roles=("parent",),
    )

    root_provider = (
        "tests.fixtures.invariant_core.category_specs_like.rings._RingObjectMethods"
    )
    commutative_provider = (
        "tests.fixtures.invariant_core.category_specs_like.rings.subcategories."
        "commutative._CommutativeRings.ParentMethods"
    )
    projection = projections[commutative_provider]
    category = _CommutativeRings.an_instance()
    runtime_to_provider = {
        category.parent_class: _CommutativeRings.ParentMethods,
        Rings.an_instance().parent_class: Rings.ParentMethods,
    }
    projected_runtime_bases = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category.parent_class.__bases__
    )
    projected_runtime_mro = tuple(
        _class_fullname(runtime_to_provider[runtime_class])
        for runtime_class in category.parent_class.__mro__
        if runtime_class in runtime_to_provider
    )

    assert projection.provider == commutative_provider
    assert projection.provider_bases == projected_runtime_bases
    assert projection.provider_mro == projected_runtime_mro
    assert projection.provider_bases == (root_provider,)
    assert projection.provider_mro == (commutative_provider, root_provider)


def test_cartesian_products_projection_matches_sage_runtime_mro() -> None:
    from sage.categories.objects import Objects  # type: ignore[import-untyped]
    from sage.categories.sets_cat import Sets  # type: ignore[import-untyped]

    projections = provider_projections_for_categories(
        (
            "tests.fixtures.invariant_core.functorial.cartesian_products."
            "CartesianProductsCategory",
        ),
        roles=("parent", "element"),
    )

    category = CartesianProductsCategory
    runtime_to_provider = {
        "parent": {
            category.parent_class: type(category).ParentMethods,
            Sets().parent_class: Sets.ParentMethods,
            Objects().parent_class: Objects.ParentMethods,
        },
        "element": {
            category.element_class: type(category).ElementMethods,
            Sets().element_class: Sets.ElementMethods,
        },
    }
    expected = {
        "parent": (
            "sage.categories.sets_cat.Sets.CartesianProducts.ParentMethods",
            category.parent_class,
            runtime_to_provider["parent"],
        ),
        "element": (
            "sage.categories.sets_cat.Sets.CartesianProducts.ElementMethods",
            category.element_class,
            runtime_to_provider["element"],
        ),
    }

    for role, (provider, runtime_class, provider_map) in expected.items():
        projection = projections[provider]
        projected_runtime_bases = tuple(
            _class_fullname(provider_map[runtime_base])
            for runtime_base in runtime_class.__bases__
            if runtime_base in provider_map
        )
        projected_runtime_mro = tuple(
            _class_fullname(provider_map[runtime_mro_class])
            for runtime_mro_class in runtime_class.__mro__
            if runtime_mro_class in provider_map
        )
        unprojected_runtime_mro = tuple(
            _class_fullname(runtime_mro_class)
            for runtime_mro_class in runtime_class.__mro__
            if runtime_mro_class not in provider_map
            and runtime_mro_class is not object
        )

        assert projection.provider == provider
        assert projection.role == role
        assert projection.runtime_class == _class_fullname(runtime_class)
        assert projection.runtime_bases == tuple(
            _class_fullname(runtime_base)
            for runtime_base in runtime_class.__bases__
        )
        assert projection.runtime_mro == tuple(
            _class_fullname(runtime_mro_class)
            for runtime_mro_class in runtime_class.__mro__
        )
        assert projection.provider_bases == projected_runtime_bases
        assert projection.provider_mro == projected_runtime_mro
        assert projection.unprojected_runtime_mro == unprojected_runtime_mro

    assert projections[
        "sage.categories.sets_cat.Sets.CartesianProducts.ParentMethods"
    ].provider_mro == (
        "sage.categories.sets_cat.Sets.CartesianProducts.ParentMethods",
        "sage.categories.sets_cat.Sets.ParentMethods",
        "sage.categories.objects.Objects.ParentMethods",
    )
    assert projections[
        "sage.categories.sets_cat.Sets.CartesianProducts.ElementMethods"
    ].provider_mro == (
        "sage.categories.sets_cat.Sets.CartesianProducts.ElementMethods",
        "sage.categories.sets_cat.Sets.ElementMethods",
    )
