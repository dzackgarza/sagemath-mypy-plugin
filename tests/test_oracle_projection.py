from __future__ import annotations

import pytest

from sage_mypy_category_plugin.imports import import_fullname
from sage_mypy_category_plugin.imports import import_module_and_qualname
from sage_mypy_category_plugin.oracle import RoleProjection
from sage_mypy_category_plugin.oracle import concrete_parent_records_for_factories
from sage_mypy_category_plugin.oracle import provider_projections_for_categories
from sage_mypy_category_plugin.oracle import named_class_traces
from sage_mypy_category_plugin.oracle import unsupported_provider_traces
from sage_mypy_category_plugin.oracle import _provider_bases_without_self
from sage_mypy_category_plugin.oracle import _project_runtime_classes
from sage_mypy_category_plugin.oracle import _provider_fullname_from_runtime_class_or_none
from tests.fixtures.invariant_core.diamond_runtime import (
    BottomCategory,
    LeftCategory,
    RightCategory,
    TopCategory,
)
from tests.fixtures.invariant_core.diamond_behavior_decorated_base import (
    DecoratedBaseCategory,
)
from tests.fixtures.invariant_core.diamond_behavior_decorated_invalid import (
    InvalidDecoratedOverrideCategory,
)
from tests.fixtures.invariant_core.diamond_behavior_decorated_valid import (
    ValidDecoratedOverrideCategory,
)
from tests.fixtures.invariant_core.functorial.cartesian_products import (
    CartesianProductsCategory,
)
from tests.fixtures.invariant_core.functorial.tensor_products import (
    TensorProductsCategory,
)
from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase
from tests.fixtures.invariant_core.parameterized import (
    ModulesOverIntegers,
    ModulesOverRationals,
    VectorSpacesOverRationals,
)
from tests.fixtures.invariant_core.provider_conflict import (
    SharedParentMethods,
    SharedProviderBottomCategory,
    SharedProviderTopCategory,
)


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


def test_runtime_projection_deduplicates_shared_provider_targets() -> None:
    class RuntimeBase:
        pass

    class RuntimeAlias(RuntimeBase):
        pass

    provider = (
        "tests.test_oracle_projection."
        "test_runtime_projection_deduplicates_shared_provider_targets.Provider"
    )

    assert _project_runtime_classes(
        (RuntimeAlias, RuntimeBase),
        {RuntimeAlias: provider, RuntimeBase: provider},
        allow_unmapped=frozenset(),
    ) == (provider,)


def test_provider_bases_omit_self_provider_after_projection() -> None:
    provider = (
        "tests.test_oracle_projection."
        "test_provider_bases_omit_self_provider_after_projection.Provider"
    )
    inherited_provider = (
        "tests.test_oracle_projection."
        "test_provider_bases_omit_self_provider_after_projection.InheritedProvider"
    )

    assert _provider_bases_without_self(
        provider,
        (provider, inherited_provider),
    ) == (inherited_provider,)


def test_projection_skips_inherited_homsets_subcategory_provider() -> None:
    projections = provider_projections_for_categories(
        (
            "tests.fixtures.invariant_core.provider_roles.homsets."
            "StandaloneHomCategory",
        ),
        roles=("subcategory",),
    )

    assert "sage.categories.homsets.Homsets.SubcategoryMethods" not in projections


def test_projection_classifies_shared_provider_with_conflicting_runtime_mros() -> None:
    provider = _class_fullname(SharedParentMethods)

    projections = provider_projections_for_categories(
        (
            "tests.fixtures.invariant_core.provider_conflict."
            "SharedProviderTopCategory",
            "tests.fixtures.invariant_core.provider_conflict."
            "SharedProviderBottomCategory",
        ),
        roles=("parent",),
    )
    unsupported_provider = {
        trace.provider: trace for trace in unsupported_provider_traces()
    }[provider]
    top_runtime_class = SharedProviderTopCategory.an_instance().parent_class
    bottom_runtime_class = SharedProviderBottomCategory.an_instance().parent_class

    assert provider not in projections
    assert unsupported_provider.role == "parent"
    assert unsupported_provider.reason == "ambiguous_runtime_mro"
    assert unsupported_provider.runtime_classes == (
        _class_fullname(top_runtime_class),
        _class_fullname(bottom_runtime_class),
    )
    assert unsupported_provider.runtime_mros == (
        tuple(
            _class_fullname(runtime_class)
            for runtime_class in top_runtime_class.__mro__
        ),
        tuple(
            _class_fullname(runtime_class)
            for runtime_class in bottom_runtime_class.__mro__
        ),
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


def test_descendant_projection_preserves_supercategory_runtime_class_identity() -> None:
    top_category = TopCategory.an_instance()
    top_parent_class = top_category.parent_class

    provider_projections_for_categories(
        ("tests.fixtures.invariant_core.diamond_runtime.BottomCategory",),
        roles=("parent",),
    )

    assert TopCategory.an_instance().parent_class is top_parent_class


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


def test_decorated_behavior_projection_matches_sage_runtime_mro() -> None:
    projections = provider_projections_for_categories(
        (
            "tests.fixtures.invariant_core.diamond_behavior_decorated_base.DecoratedBaseCategory",
            "tests.fixtures.invariant_core.diamond_behavior_decorated_valid.ValidDecoratedOverrideCategory",
            "tests.fixtures.invariant_core.diamond_behavior_decorated_invalid.InvalidDecoratedOverrideCategory",
        ),
        roles=("parent",),
    )
    expected_chains = {
        DecoratedBaseCategory: (
            "tests.fixtures.invariant_core.diamond_behavior_decorated_base.DecoratedBaseCategory.ParentMethods",
            (
                "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods",
            ),
            (
                "tests.fixtures.invariant_core.diamond_behavior_decorated_base.DecoratedBaseCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.RightCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
            ),
        ),
        ValidDecoratedOverrideCategory: (
            "tests.fixtures.invariant_core.diamond_behavior_decorated_valid.ValidDecoratedOverrideCategory.ParentMethods",
            (
                "tests.fixtures.invariant_core.diamond_behavior_decorated_base.DecoratedBaseCategory.ParentMethods",
            ),
            (
                "tests.fixtures.invariant_core.diamond_behavior_decorated_valid.ValidDecoratedOverrideCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_behavior_decorated_base.DecoratedBaseCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.RightCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
            ),
        ),
        InvalidDecoratedOverrideCategory: (
            "tests.fixtures.invariant_core.diamond_behavior_decorated_invalid.InvalidDecoratedOverrideCategory.ParentMethods",
            (
                "tests.fixtures.invariant_core.diamond_behavior_decorated_base.DecoratedBaseCategory.ParentMethods",
            ),
            (
                "tests.fixtures.invariant_core.diamond_behavior_decorated_invalid.InvalidDecoratedOverrideCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_behavior_decorated_base.DecoratedBaseCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.BottomCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.RightCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.LeftCategory.ParentMethods",
                "tests.fixtures.invariant_core.diamond_runtime.TopCategory.ParentMethods",
            ),
        ),
    }

    for category_type, (
        provider,
        expected_bases,
        expected_mro,
    ) in expected_chains.items():
        category = category_type.an_instance()
        projection = projections[provider]

        assert projection.runtime_bases == tuple(
            _class_fullname(runtime_class)
            for runtime_class in category.parent_class.__bases__
        )
        assert projection.runtime_mro == tuple(
            _class_fullname(runtime_class)
            for runtime_class in category.parent_class.__mro__
        )
        assert projection.provider_bases == expected_bases
        assert projection.provider_mro == expected_mro


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


def test_tensor_products_projection_records_projectable_runtime_bases() -> None:
    projections = provider_projections_for_categories(
        (
            "tests.fixtures.invariant_core.functorial.tensor_products."
            "TensorProductsCategory",
        ),
        roles=("parent",),
    )

    projection = projections["sage.categories.modules.Modules.TensorProducts.ParentMethods"]
    runtime_class = TensorProductsCategory.parent_class.__bases__[0]

    assert _class_fullname(runtime_class) == (
        "sage.categories.modules.Modules.TensorProducts.parent_class"
    )
    assert projection.provider == (
        "sage.categories.modules.Modules.TensorProducts.ParentMethods"
    )
    assert projection.runtime_class == _class_fullname(runtime_class)
    assert projection.runtime_bases == tuple(
        _class_fullname(runtime_base)
        for runtime_base in runtime_class.__bases__
    )
    assert projection.runtime_mro == tuple(
        _class_fullname(runtime_mro_class)
        for runtime_mro_class in runtime_class.__mro__
    )
    assert projection.provider_bases == (
        "sage.categories.modules.Modules.ParentMethods",
    )
    assert projection.provider_mro == (
        "sage.categories.modules.Modules.TensorProducts.ParentMethods",
        "sage.categories.modules.Modules.ParentMethods",
        "sage.categories.bimodules.Bimodules.ParentMethods",
        "sage.categories.right_modules.RightModules.ParentMethods",
        "sage.categories.left_modules.LeftModules.ParentMethods",
        "sage.categories.additive_monoids.AdditiveMonoids.ParentMethods",
        "sage.categories.additive_magmas.AdditiveMagmas.AdditiveUnital.ParentMethods",
        "sage.categories.additive_semigroups.AdditiveSemigroups.ParentMethods",
        "sage.categories.additive_magmas.AdditiveMagmas.ParentMethods",
        "sage.categories.sets_cat.Sets.ParentMethods",
        "sage.categories.objects.Objects.ParentMethods",
    )
    assert projection.unprojected_runtime_mro == (
        "sage.categories.commutative_additive_groups.CommutativeAdditiveGroups.parent_class",
        "sage.categories.additive_groups.AdditiveGroups.parent_class",
        "sage.categories.additive_magmas.AdditiveMagmas.AdditiveUnital.AdditiveInverse.parent_class",
        "sage.categories.commutative_additive_monoids.CommutativeAdditiveMonoids.parent_class",
        "sage.categories.commutative_additive_semigroups.CommutativeAdditiveSemigroups.parent_class",
        "sage.categories.additive_magmas.AdditiveMagmas.AdditiveCommutative.parent_class",
        "sage.categories.sets_with_partial_maps.SetsWithPartialMaps.parent_class",
    )


def test_parameterized_projection_uses_sage_runtime_named_class_identity() -> None:
    projections = provider_projections_for_categories(
        (
            "tests.fixtures.invariant_core.parameterized.ModulesOverIntegers",
            "tests.fixtures.invariant_core.parameterized.ModulesOverRationals",
            "tests.fixtures.invariant_core.parameterized.VectorSpacesOverRationals",
        ),
        roles=("parent",),
    )

    modules_provider = "sage.categories.modules.Modules.ParentMethods"
    vector_spaces_provider = "sage.categories.vector_spaces.VectorSpaces.ParentMethods"
    modules_projection = projections[modules_provider]
    vector_spaces_projection = projections[vector_spaces_provider]

    assert ModulesOverRationals.parent_class is VectorSpacesOverRationals.parent_class
    assert ModulesOverIntegers.parent_class is not ModulesOverRationals.parent_class
    assert modules_projection.runtime_class == _class_fullname(
        ModulesOverIntegers.parent_class
    )
    assert vector_spaces_projection.runtime_class == _class_fullname(
        VectorSpacesOverRationals.parent_class
    )
    assert vector_spaces_projection.runtime_class == _class_fullname(
        ModulesOverRationals.parent_class
    )
    assert vector_spaces_projection.provider_bases == (modules_provider,)
    assert vector_spaces_projection.provider_mro[:2] == (
        vector_spaces_provider,
        modules_provider,
    )
    assert modules_projection.provider_mro[0] == modules_provider
    assert modules_projection.runtime_class != vector_spaces_projection.runtime_class


def test_concrete_parent_record_matches_sage_initialized_category() -> None:
    concrete_class = import_fullname(
        "sage.categories.examples.semigroups.LeftZeroSemigroup"
    )
    assert isinstance(concrete_class, type)
    parent = concrete_class()
    records = concrete_parent_records_for_factories(
        ("sage.categories.examples.semigroups.LeftZeroSemigroup",),
    )

    record = records["sage.categories.examples.semigroups.LeftZeroSemigroup"]

    assert record.concrete_class == (
        "sage.categories.examples.semigroups.LeftZeroSemigroup"
    )
    assert record.runtime_class == (
        "sage.categories.examples.semigroups.LeftZeroSemigroup_with_category"
    )
    assert record.category_class == "sage.categories.semigroups.Semigroups_with_category"
    assert record.parent_provider_mro[:2] == (
        "sage.categories.semigroups.Semigroups.ParentMethods",
        "sage.categories.magmas.Magmas.ParentMethods",
    )
    assert record.element_runtime_class == (
        "sage.categories.examples.semigroups.LeftZeroSemigroup_with_category."
        "element_class"
    )
    assert record.element_runtime_mro == tuple(
        _class_fullname(base) for base in parent.element_class.__mro__
    )
    assert "sage.structure.element.Element" in record.element_runtime_mro
    assert record.element_provider_mro[:2] == (
        "sage.categories.semigroups.Semigroups.ElementMethods",
        "sage.categories.magmas.Magmas.ElementMethods",
    )


def test_import_module_and_qualname_rejects_single_part_name() -> None:
    """import_module_and_qualname requires a dotted (fully-qualified) name.

    A single identifier like 'builtins' has no module/qualname split and is
    rejected with ValueError before any import attempt.  This boundary check
    prevents callers from accidentally passing bare module names as fullnames.
    """
    with pytest.raises(ValueError, match="fully-qualified"):
        import_module_and_qualname("singlepart")


def test_import_fullname_raises_attribute_error_with_context() -> None:
    """import_fullname reports the fullname and missing attribute in the error.

    The AttributeError message embeds the full dotted name and the missing
    attribute name, giving callers enough context to diagnose broken references
    in category manifests without reading a bare AttributeError from the
    object repr.
    """
    with pytest.raises(AttributeError) as raised:
        import_fullname("builtins.int.nonexistent_sage_method_xyz")

    message = str(raised.value)
    assert "nonexistent_sage_method_xyz" in message
    assert "builtins.int.nonexistent_sage_method_xyz" in message


def test_import_module_and_qualname_raises_when_no_prefix_importable() -> None:
    """import_module_and_qualname raises ModuleNotFoundError for fully unknown names.

    When no prefix of the dotted name resolves to an importable module, the
    function raises ModuleNotFoundError (not AttributeError or ValueError).
    This happens for names that belong to packages not installed in the
    environment.
    """
    with pytest.raises(ModuleNotFoundError):
        import_module_and_qualname(
            "nonexistent_package_sage_xyz.SubClass.method"
        )
