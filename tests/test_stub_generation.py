from __future__ import annotations

from pathlib import Path

from sage_mypy_category_plugin.manifest import ProjectionManifest, SourceModuleRecord
from sage_mypy_category_plugin.projection import ProviderProjection
from sage_mypy_category_plugin.stubs import generated_stub_sources


def test_generated_stubs_reproduce_provider_tree_from_manifest() -> None:
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=(
            ProviderProjection(
                provider="sage.categories.objects.Objects.ParentMethods",
                role="parent",
                runtime_class="sage.categories.objects.Objects.parent_class",
                runtime_bases=("builtins.object",),
                runtime_mro=(
                    "sage.categories.objects.Objects.parent_class",
                    "builtins.object",
                ),
                provider_bases=(),
                provider_mro=("sage.categories.objects.Objects.ParentMethods",),
            ),
            ProviderProjection(
                provider="sage.categories.sets_cat.Sets.ParentMethods",
                role="parent",
                runtime_class="sage.categories.sets_cat.Sets.parent_class",
                runtime_bases=("sage.categories.objects.Objects.parent_class",),
                runtime_mro=(
                    "sage.categories.sets_cat.Sets.parent_class",
                    "sage.categories.objects.Objects.parent_class",
                    "builtins.object",
                ),
                provider_bases=("sage.categories.objects.Objects.ParentMethods",),
                provider_mro=(
                    "sage.categories.sets_cat.Sets.ParentMethods",
                    "sage.categories.objects.Objects.ParentMethods",
                ),
            ),
            ProviderProjection(
                provider="sage.categories.sets_cat.Sets.ElementMethods",
                role="element",
                runtime_class="sage.categories.sets_cat.Sets.element_class",
                runtime_bases=("builtins.object",),
                runtime_mro=(
                    "sage.categories.sets_cat.Sets.element_class",
                    "builtins.object",
                ),
                provider_bases=(),
                provider_mro=("sage.categories.sets_cat.Sets.ElementMethods",),
            ),
            ProviderProjection(
                provider="sage.categories.sets_cat.Sets.CartesianProducts.ParentMethods",
                role="parent",
                runtime_class="sage.categories.sets_cat.Sets.CartesianProducts.parent_class",
                runtime_bases=("sage.categories.sets_cat.Sets.parent_class",),
                runtime_mro=(
                    "sage.categories.sets_cat.Sets.CartesianProducts.parent_class",
                    "sage.categories.sets_cat.Sets.parent_class",
                    "sage.categories.objects.Objects.parent_class",
                    "builtins.object",
                ),
                provider_bases=("sage.categories.sets_cat.Sets.ParentMethods",),
                provider_mro=(
                    "sage.categories.sets_cat.Sets.CartesianProducts.ParentMethods",
                    "sage.categories.sets_cat.Sets.ParentMethods",
                    "sage.categories.objects.Objects.ParentMethods",
                ),
            ),
            ProviderProjection(
                provider="sage.categories.sets_cat.Sets.CartesianProducts.ElementMethods",
                role="element",
                runtime_class="sage.categories.sets_cat.Sets.CartesianProducts.element_class",
                runtime_bases=("sage.categories.sets_cat.Sets.element_class",),
                runtime_mro=(
                    "sage.categories.sets_cat.Sets.CartesianProducts.element_class",
                    "sage.categories.sets_cat.Sets.element_class",
                    "builtins.object",
                ),
                provider_bases=("sage.categories.sets_cat.Sets.ElementMethods",),
                provider_mro=(
                    "sage.categories.sets_cat.Sets.CartesianProducts.ElementMethods",
                    "sage.categories.sets_cat.Sets.ElementMethods",
                ),
            ),
        ),
        source_modules=(
            SourceModuleRecord(
                module="sage.categories.objects",
                path="sage/categories/objects.py",
                sha256="0" * 64,
            ),
            SourceModuleRecord(
                module="sage.categories.sets_cat",
                path="sage/categories/sets_cat.py",
                sha256="1" * 64,
            ),
        ),
    )

    assert generated_stub_sources(manifest) == {
        Path("sage/categories/objects.pyi"): (
            "class Objects:\n"
            "    class ParentMethods:\n"
            "        ...\n"
        ),
        Path("sage/categories/sets_cat.pyi"): (
            "class Sets:\n"
            "    class ElementMethods:\n"
            "        ...\n"
            "    class ParentMethods:\n"
            "        ...\n"
            "    class CartesianProducts:\n"
            "        class ElementMethods:\n"
            "            ...\n"
            "        class ParentMethods:\n"
            "            ...\n"
        ),
    }
