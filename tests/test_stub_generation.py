from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from mypy.build import BuildResult, build
from mypy.modulefinder import BuildSource
from mypy.options import Options

from sage_mypy_category_plugin.manifest import ProjectionManifest, SourceModuleRecord
from sage_mypy_category_plugin.projection import ProviderProjection
from sage_mypy_category_plugin.stubs import generated_stub_sources
from sage_mypy_category_plugin.stubs import write_generated_stub_tree


def test_generated_stubs_support_manifest_projected_annotation_behavior(
    tmp_path: Path,
) -> None:
    manifest = _sets_cartesian_products_manifest()
    stub_root = tmp_path / "generated-stubs"
    source_modules = write_generated_stub_tree(stub_root, manifest)
    plugin_manifest = manifest.model_copy(update={"source_modules": source_modules})
    manifest_path = tmp_path / "manifest.json"
    config_path = tmp_path / "mypy.ini"
    consumer_path = tmp_path / "consumer.py"
    manifest_path.write_text(plugin_manifest.model_dump_json())
    config_path.write_text(
        "\n".join(
            (
                "[mypy]",
                "plugins = sage_mypy_category_plugin.plugin",
                "",
                "[sage-mypy-category-plugin]",
                f"manifest = {manifest_path}",
                "",
            )
        )
    )
    consumer_path.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "from sage.categories.sets_cat import Sets",
                "",
                "def parent_provider(",
                "    provider: Sets.CartesianProducts.ParentMethods,",
                ") -> Sets.ParentMethods:",
                "    return provider",
                "",
                "def element_provider(",
                "    provider: Sets.CartesianProducts.ElementMethods,",
                ") -> Sets.ElementMethods:",
                "    return provider",
                "",
            )
        )
    )

    with_plugin = _run_mypy(
        consumer_path,
        mypy_path_entries=(stub_root,),
        config_path=config_path,
    )
    without_plugin = _run_mypy(
        consumer_path,
        mypy_path_entries=(stub_root,),
        config_path=None,
    )

    assert with_plugin.errors == []
    assert any("[return-value]" in error for error in without_plugin.errors)


def test_generated_stubs_reproduce_provider_tree_from_manifest() -> None:
    manifest = _sets_cartesian_products_manifest()

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


def test_generated_stub_tree_records_written_source_metadata(tmp_path: Path) -> None:
    stub_root = tmp_path / "generated-stubs"

    source_modules = write_generated_stub_tree(
        stub_root,
        _sets_cartesian_products_manifest(),
    )
    source_module_by_module = {record.module: record for record in source_modules}
    sets_record = source_module_by_module["sage.categories.sets_cat"]
    sets_path = Path(sets_record.path)

    assert sets_record.sha256 == sha256(sets_path.read_bytes()).hexdigest()
    assert sets_record.mtime_ns == sets_path.stat().st_mtime_ns


def _sets_cartesian_products_manifest() -> ProjectionManifest:
    return ProjectionManifest(
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
                mtime_ns=1_789_000_000_000_000_000,
            ),
            SourceModuleRecord(
                module="sage.categories.sets_cat",
                path="sage/categories/sets_cat.py",
                sha256="1" * 64,
                mtime_ns=1_789_000_000_000_000_001,
            ),
        ),
    )


def _run_mypy(
    source_path: Path,
    *,
    mypy_path_entries: tuple[Path, ...],
    config_path: Path | None,
) -> BuildResult:
    options = Options()
    options.incremental = False
    options.cache_dir = str(source_path.parent / f"{config_path is not None}-cache")
    options.mypy_path = [str(path) for path in mypy_path_entries]
    if config_path is not None:
        options.config_file = str(config_path)
        options.plugins = ["sage_mypy_category_plugin.plugin"]
    return build(
        sources=[BuildSource(str(source_path), "consumer", None)],
        options=options,
    )
