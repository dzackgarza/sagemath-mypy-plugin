from __future__ import annotations

import ast
from hashlib import sha256
from pathlib import Path

from mypy.build import BuildResult, build
from mypy.modulefinder import BuildSource
from mypy.options import Options

from sage_mypy_category_plugin.manifest import (
    ProjectionManifest,
    SourceModuleRecord,
    load_manifest,
)
from sage_mypy_category_plugin.projection import ConcreteParentRecord
from sage_mypy_category_plugin.projection import ExternalRuntimeClassRecord
from sage_mypy_category_plugin.projection import ProviderMethodRecord
from sage_mypy_category_plugin.projection import ProviderProjection
from sage_mypy_category_plugin import stubs as stubs_cli
from sage_mypy_category_plugin.static_stubs import static_stub_sources
from sage_mypy_category_plugin.stubs import generated_stub_sources
from sage_mypy_category_plugin.stubs import write_generated_stub_tree


def test_static_stubs_are_syntactically_valid_python() -> None:
    """Every hand-maintained static stub in static_stubs.py must be valid Python syntax.

    A syntax error in a static stub surfaces as a confusing mypy parse error rather
    than a clear diagnostic pointing at the stub source.  This test proves that all
    non-empty stub sources in _STUB_SOURCES are parseable by the Python AST, catching
    any malformed stub before it reaches a mypy run.
    """
    for path, source in static_stub_sources().items():
        if not source:
            # Empty __init__.pyi package markers have no content to validate.
            continue
        try:
            ast.parse(source, filename=str(path), type_comments=False)
        except SyntaxError as exc:
            raise AssertionError(
                f"Static stub {path} has a syntax error: {exc}"
            ) from exc


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


def test_generated_stubs_define_sibling_provider_bases_before_dependents(
    tmp_path: Path,
) -> None:
    manifest = _sets_subobjects_manifest()
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
                "def subobject_parent(",
                "    provider: Sets.Subobjects.ParentMethods,",
                ") -> Sets.Subquotients.ParentMethods:",
                "    return provider",
                "",
            )
        )
    )

    generated_source = (stub_root / "sage/categories/sets_cat.pyi").read_text()
    with_plugin = _run_mypy(
        consumer_path,
        mypy_path_entries=(stub_root,),
        config_path=config_path,
    )

    assert generated_source.index("class Subquotients:") < generated_source.index(
        "class Subobjects:"
    )
    assert with_plugin.errors == []


def test_generated_stubs_define_subcategory_bases_before_nested_dependents(
    tmp_path: Path,
) -> None:
    top_provider = "fixture.Top.SubcategoryMethods"
    child_provider = "fixture.Top.Child.SubcategoryMethods"
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=(
            ProviderProjection(
                provider=top_provider,
                role="subcategory",
                runtime_class="fixture.Top.subcategory_class",
                runtime_bases=("builtins.object",),
                runtime_mro=("fixture.Top.subcategory_class", "builtins.object"),
                provider_bases=(),
                provider_mro=(top_provider,),
            ),
            ProviderProjection(
                provider=child_provider,
                role="subcategory",
                runtime_class="fixture.Top.Child.subcategory_class",
                runtime_bases=("fixture.Top.subcategory_class",),
                runtime_mro=(
                    "fixture.Top.Child.subcategory_class",
                    "fixture.Top.subcategory_class",
                    "builtins.object",
                ),
                provider_bases=(top_provider,),
                provider_mro=(child_provider, top_provider),
            ),
        ),
        source_modules=(
            SourceModuleRecord(
                module="fixture",
                path=str(tmp_path / "fixture.py"),
                sha256="0" * 64,
                mtime_ns=0,
            ),
        ),
    )
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
                "from fixture import Top",
                "",
                "Top.Child.SubcategoryMethods",
                "",
            )
        )
    )

    generated_source = (stub_root / "fixture.pyi").read_text()
    with_plugin = _run_mypy(
        consumer_path,
        mypy_path_entries=(stub_root,),
        config_path=config_path,
    )

    assert generated_source.index("class SubcategoryMethods:") < generated_source.index(
        "class Child:"
    )
    assert "class SubcategoryMethods:" in generated_source
    assert with_plugin.errors == []


def test_generated_stubs_import_cross_module_provider_bases(tmp_path: Path) -> None:
    base_provider = "base_provider.BaseCategory.ParentMethods"
    child_provider = "consumer_mod.ConsumerCategory.ParentMethods"
    manifest = ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=(
            ProviderProjection(
                provider=base_provider,
                role="parent",
                runtime_class="base_provider.BaseCategory.parent_class",
                runtime_bases=("builtins.object",),
                runtime_mro=(
                    "base_provider.BaseCategory.parent_class",
                    "builtins.object",
                ),
                provider_bases=(),
                provider_mro=(base_provider,),
            ),
            ProviderProjection(
                provider=child_provider,
                role="parent",
                runtime_class="consumer_mod.ConsumerCategory.parent_class",
                runtime_bases=("base_provider.BaseCategory.parent_class",),
                runtime_mro=(
                    "consumer_mod.ConsumerCategory.parent_class",
                    "base_provider.BaseCategory.parent_class",
                    "builtins.object",
                ),
                provider_bases=(base_provider,),
                provider_mro=(child_provider, base_provider),
            ),
        ),
        source_modules=(
            SourceModuleRecord(
                module="base_provider",
                path=str(tmp_path / "base_provider.py"),
                sha256="0" * 64,
                mtime_ns=0,
            ),
            SourceModuleRecord(
                module="consumer_mod",
                path=str(tmp_path / "consumer_mod.py"),
                sha256="0" * 64,
                mtime_ns=0,
            ),
        ),
    )
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
                "from consumer_mod import ConsumerCategory",
                "",
                "ConsumerCategory.ParentMethods",
                "",
            )
        )
    )

    generated_source = (stub_root / "consumer_mod.pyi").read_text()
    with_plugin = _run_mypy(
        consumer_path,
        mypy_path_entries=(stub_root,),
        config_path=config_path,
    )

    # The plugin injects the MRO at analysis time; generated stubs do not
    # declare provider_bases as explicit class bases (that is the plugin's job).
    assert "class ConsumerCategory:" in generated_source
    assert "class ParentMethods:" in generated_source
    # No cross-module import in the stub — the plugin wires the MRO.
    assert "from base_provider import BaseCategory" not in generated_source
    assert with_plugin.errors == []


def test_generated_stubs_reproduce_provider_tree_from_manifest() -> None:
    manifest = _sets_cartesian_products_manifest()

    assert generated_stub_sources(manifest) == {
        Path("_sage_category_types.pyi"): (
            "from sage.categories.objects import Objects\n"
            "from sage.categories.sets_cat import Sets\n"
            "\n"
            "class sage_categories_objects__Objects__parent_class(\n"
            "    Objects.ParentMethods,\n"
            "):\n"
            "    ...\n"
            "\n"
            "class sage_categories_sets_cat__Sets__CartesianProducts__element_class(\n"
            "    Sets.CartesianProducts.ElementMethods,\n"
            "    Sets.ElementMethods,\n"
            "):\n"
            "    ...\n"
            "\n"
            "class sage_categories_sets_cat__Sets__CartesianProducts__parent_class(\n"
            "    Sets.CartesianProducts.ParentMethods,\n"
            "    Sets.ParentMethods,\n"
            "    Objects.ParentMethods,\n"
            "):\n"
            "    ...\n"
            "\n"
            "class sage_categories_sets_cat__Sets__element_class(\n"
            "    Sets.ElementMethods,\n"
            "):\n"
            "    ...\n"
            "\n"
            "class sage_categories_sets_cat__Sets__parent_class(\n"
            "    Sets.ParentMethods,\n"
            "    Objects.ParentMethods,\n"
            "):\n"
            "    ...\n"
        ),
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


def test_generated_stubs_materialize_receiver_method_records() -> None:
    manifest = _sets_cartesian_products_manifest().model_copy(
        update={
            "provider_methods": (
                ProviderMethodRecord(
                    provider="sage.categories.objects.Objects.ParentMethods",
                    name="_an_element_",
                    return_type="object",
                ),
            )
        }
    )

    assert generated_stub_sources(manifest)[Path("sage/categories/objects.pyi")] == (
        "class Objects:\n"
        "    class ParentMethods:\n"
        "        def _an_element_(self) -> object: ...\n"
    )


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


def test_generated_stub_cli_writes_stub_tree(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    output_root = tmp_path / "generated-stubs"
    manifest_path.write_text(_self_return_provider_manifest().model_dump_json())

    assert stubs_cli.main([str(manifest_path), str(output_root)]) == 0

    assert (output_root / "fixtures" / "self_type.pyi").read_text() == (
        "from typing import Self\n"
        "\n"
        "class BaseCategory:\n"
        "    class ParentMethods:\n"
        "        def normalized(self) -> Self: ...\n"
        "class ChildCategory:\n"
        "    class ParentMethods:\n"
        "        ...\n"
    )


def test_generated_stub_cli_writes_manifest_with_stub_source_metadata(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    output_root = tmp_path / "generated-stubs"
    manifest_output_path = tmp_path / "manifest.with-stubs.json"
    manifest_path.write_text(_self_return_provider_manifest().model_dump_json())

    assert (
        stubs_cli.main(
            [
                str(manifest_path),
                str(output_root),
                "--manifest-output",
                str(manifest_output_path),
            ]
        )
        == 0
    )

    stub_manifest = load_manifest(manifest_output_path)
    source_record = stub_manifest.source_module_by_module["fixtures.self_type"]
    source_path = Path(source_record.path)

    assert source_path == output_root / "fixtures" / "self_type.pyi"
    assert source_record.sha256 == sha256(source_path.read_bytes()).hexdigest()
    assert source_record.mtime_ns == source_path.stat().st_mtime_ns


def test_generated_stub_cli_preserves_requested_source_modules(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    source_path = source_root / "fixtures" / "self_type.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        "\n".join(
            (
                "class BaseCategory:",
                "    class ParentMethods:",
                "        pass",
                "class ChildCategory:",
                "    class ParentMethods:",
                "        pass",
                "",
            )
        )
    )
    source_record = SourceModuleRecord(
        module="fixtures.self_type",
        path=str(source_path),
        sha256=sha256(source_path.read_bytes()).hexdigest(),
        mtime_ns=source_path.stat().st_mtime_ns,
    )
    manifest = _self_return_provider_manifest().model_copy(
        update={"source_modules": (source_record,)}
    )
    manifest_path = tmp_path / "manifest.json"
    output_root = tmp_path / "generated-stubs"
    manifest_output_path = tmp_path / "manifest.with-stubs.json"
    manifest_path.write_text(manifest.model_dump_json())

    assert (
        stubs_cli.main(
            [
                str(manifest_path),
                str(output_root),
                "--manifest-output",
                str(manifest_output_path),
                "--preserve-source-module-prefix",
                "fixtures",
            ]
        )
        == 0
    )

    stub_manifest = load_manifest(manifest_output_path)

    assert not (output_root / "fixtures" / "self_type.pyi").exists()
    assert (output_root / "_sage_category_types.pyi").is_file()
    assert stub_manifest.source_module_by_module["fixtures.self_type"] == source_record


def test_generated_stub_cli_keeps_external_runtime_source_modules(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source" / "sage" / "categories" / (
        "sets_with_partial_maps.py"
    )
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        "\n".join(
            (
                "class SetsWithPartialMaps:",
                "    class parent_class:",
                "        pass",
                "",
            )
        )
    )
    external_source = SourceModuleRecord(
        module="sage.categories.sets_with_partial_maps",
        path=str(source_path),
        sha256=sha256(source_path.read_bytes()).hexdigest(),
        mtime_ns=source_path.stat().st_mtime_ns,
    )
    external_runtime = ExternalRuntimeClassRecord(
        runtime_class=(
            "sage.categories.sets_with_partial_maps."
            "SetsWithPartialMaps.parent_class"
        ),
        module="sage.categories.sets_with_partial_maps",
        static_signature_source="python_source",
        source_module=external_source.module,
    )
    base_manifest = _sets_cartesian_products_manifest()
    projection = base_manifest.projections[1].model_copy(
        update={"unprojected_runtime_mro": (external_runtime.runtime_class,)}
    )
    manifest = base_manifest.model_copy(
        update={
            "projections": (
                base_manifest.projections[0],
                projection,
                *base_manifest.projections[2:],
            ),
            "external_runtime_classes": (external_runtime,),
            "source_modules": (*base_manifest.source_modules, external_source),
        }
    )
    manifest_path = tmp_path / "manifest.json"
    output_root = tmp_path / "generated-stubs"
    manifest_output_path = tmp_path / "manifest.with-stubs.json"
    manifest_path.write_text(manifest.model_dump_json())

    assert (
        stubs_cli.main(
            [
                str(manifest_path),
                str(output_root),
                "--manifest-output",
                str(manifest_output_path),
            ]
        )
        == 0
    )

    stub_manifest = load_manifest(manifest_output_path)

    assert stub_manifest.external_runtime_classes == (external_runtime,)
    assert (
        stub_manifest.source_module_by_module[external_source.module]
        == external_source
    )


def test_generated_stub_cli_uses_generated_module_once_for_external_runtime_overlap(
    tmp_path: Path,
) -> None:
    external_runtime = ExternalRuntimeClassRecord(
        runtime_class="sage.categories.objects.Objects.element_class",
        module="sage.categories.objects",
        static_signature_source="python_source",
        source_module="sage.categories.objects",
    )
    base_manifest = _sets_cartesian_products_manifest()
    projection = base_manifest.projections[0].model_copy(
        update={"unprojected_runtime_mro": (external_runtime.runtime_class,)}
    )
    manifest = base_manifest.model_copy(
        update={
            "projections": (projection, *base_manifest.projections[1:]),
            "external_runtime_classes": (external_runtime,),
        }
    )
    manifest_path = tmp_path / "manifest.json"
    output_root = tmp_path / "generated-stubs"
    manifest_output_path = tmp_path / "manifest.with-stubs.json"
    manifest_path.write_text(manifest.model_dump_json())

    assert (
        stubs_cli.main(
            [
                str(manifest_path),
                str(output_root),
                "--manifest-output",
                str(manifest_output_path),
            ]
        )
        == 0
    )

    stub_manifest = load_manifest(manifest_output_path)
    source_record = stub_manifest.source_module_by_module["sage.categories.objects"]

    assert source_record.path == str(output_root / "sage/categories/objects.pyi")
    assert tuple(
        record.module
        for record in stub_manifest.source_modules
        if record.module == "sage.categories.objects"
    ) == ("sage.categories.objects",)


def test_generated_stubs_shell_untyped_external_runtime_classes(
    tmp_path: Path,
) -> None:
    external_runtime = ExternalRuntimeClassRecord(
        runtime_class="sage.structure.parent.Parent",
        module="sage.structure.parent",
        static_signature_source="untyped_external",
    )
    manifest = _sets_cartesian_products_manifest().model_copy(
        update={"external_runtime_classes": (external_runtime,)}
    )
    stub_root = tmp_path / "generated-stubs"
    source_modules = write_generated_stub_tree(stub_root, manifest)
    consumer_path = tmp_path / "consumer.py"
    consumer_path.write_text(
        "\n".join(
            (
                "from sage.structure.parent import Parent as SageParent",
                "",
                "CategoryObject = SageParent",
                "",
                "def valid_alias(value: CategoryObject) -> CategoryObject:",
                "    return value",
                "",
                "def invalid_signature_claim(value: CategoryObject) -> object:",
                "    return value.structure_morphism()",
                "",
            )
        )
    )

    result = _run_mypy(
        consumer_path,
        mypy_path_entries=(stub_root,),
        config_path=None,
    )
    source_record = {
        record.module: record for record in source_modules
    }["sage.structure.parent"]

    assert source_record.path == str(stub_root / "sage/structure/parent.pyi")
    assert (stub_root / "sage/structure/parent.pyi").read_text() == (
        "class Parent:\n"
        "    ...\n"
    )
    assert result.errors == [
        f'{consumer_path}:9: error: "Parent" has no attribute '
        '"structure_morphism"  [attr-defined]',
    ]


def test_generated_stubs_preserve_source_prefix_but_shell_untyped_external() -> None:
    external_runtime = ExternalRuntimeClassRecord(
        runtime_class="sage.categories.morphism.Morphism",
        module="sage.categories.morphism",
        static_signature_source="untyped_external",
    )
    manifest = _sets_cartesian_products_manifest().model_copy(
        update={"external_runtime_classes": (external_runtime,)}
    )

    sources = generated_stub_sources(
        manifest,
        preserved_source_module_prefixes=("sage.categories",),
    )

    assert sources[Path("sage/categories/morphism.pyi")] == (
        "class Morphism:\n"
        "    ...\n"
    )
    assert Path("sage/categories/sets_cat.pyi") not in sources


def test_generated_stubs_include_concrete_parent_runtime_aliases() -> None:
    manifest = _left_zero_semigroup_concrete_parent_manifest()

    assert generated_stub_sources(manifest)[Path("_sage_category_types.pyi")] == (
        "from sage.categories.examples.semigroups import LeftZeroSemigroup\n"
        "from sage.categories.semigroups import Semigroups\n"
        "\n"
        "class sage_categories_examples_semigroups__LeftZeroSemigroup_with_category(\n"
        "    LeftZeroSemigroup,\n"
        "    Semigroups.ParentMethods,\n"
        "):\n"
        "    ...\n"
        "\n"
        "class sage_categories_examples_semigroups__LeftZeroSemigroup_with_category__element_class(\n"
        "    Semigroups.ElementMethods,\n"
        "):\n"
        "    ...\n"
        "\n"
        "class sage_categories_semigroups__Semigroups__element_class(\n"
        "    Semigroups.ElementMethods,\n"
        "):\n"
        "    ...\n"
        "\n"
        "class sage_categories_semigroups__Semigroups__parent_class(\n"
        "    Semigroups.ParentMethods,\n"
        "):\n"
        "    ...\n"
    )


def test_generated_stubs_bind_concrete_parent_runtime_alias_to_concrete_class(
    tmp_path: Path,
) -> None:
    manifest = _left_zero_semigroup_concrete_parent_manifest()
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
                "from _sage_category_types import (",
                "    sage_categories_examples_semigroups__LeftZeroSemigroup_with_category,",
                ")",
                "from sage.categories.examples.semigroups import LeftZeroSemigroup",
                "from sage.categories.semigroups import Semigroups",
                "",
                "def concrete_parent(",
                "    parent: sage_categories_examples_semigroups__LeftZeroSemigroup_with_category,",
                ") -> LeftZeroSemigroup:",
                "    return parent",
                "",
                "def category_parent_provider(",
                "    parent: sage_categories_examples_semigroups__LeftZeroSemigroup_with_category,",
                ") -> Semigroups.ParentMethods:",
                "    return parent",
                "",
                "def invalid_element_provider(",
                "    parent: sage_categories_examples_semigroups__LeftZeroSemigroup_with_category,",
                ") -> Semigroups.ElementMethods:",
                "    return parent",
                "",
            )
        )
    )

    result = _run_mypy(
        consumer_path,
        mypy_path_entries=(stub_root,),
        config_path=config_path,
    )

    assert result.errors == [
        (
            f"{consumer_path}:20: error: Incompatible return value type "
            '(got "sage_categories_examples_semigroups__LeftZeroSemigroup_with_category", '
            'expected "ElementMethods")  [return-value]'
        ),
    ]


def test_generated_stubs_bind_concrete_parent_class_to_parent_provider(
    tmp_path: Path,
) -> None:
    manifest = _left_zero_semigroup_concrete_parent_manifest()
    stub_root = tmp_path / "generated-stubs"
    write_generated_stub_tree(stub_root, manifest)
    consumer_path = tmp_path / "consumer.py"
    consumer_path.write_text(
        "\n".join(
            (
                "from sage.categories.examples.semigroups import LeftZeroSemigroup",
                "from sage.categories.semigroups import Semigroups",
                "",
                "def category_parent_provider(",
                "    parent: LeftZeroSemigroup,",
                ") -> Semigroups.ParentMethods:",
                "    return parent",
                "",
                "def invalid_element_provider(",
                "    parent: LeftZeroSemigroup,",
                ") -> Semigroups.ElementMethods:",
                "    return parent",
                "",
            )
        )
    )

    result = _run_mypy(
        consumer_path,
        mypy_path_entries=(stub_root,),
        config_path=None,
    )

    assert result.errors == [
        (
            f"{consumer_path}:12: error: Incompatible return value type "
            '(got "LeftZeroSemigroup", expected "ElementMethods")  [return-value]'
        ),
    ]


def test_generated_stubs_bind_inherited_provider_self_return(
    tmp_path: Path,
) -> None:
    manifest = _self_return_provider_manifest()
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
                "from fixtures.self_type import BaseCategory, ChildCategory",
                "",
                "def child_self(",
                "    provider: ChildCategory.ParentMethods,",
                ") -> ChildCategory.ParentMethods:",
                "    normalized = provider.normalized()",
                "    reveal_type(normalized)",
                "    return normalized",
                "",
                "def invalid_base_to_child(",
                "    provider: BaseCategory.ParentMethods,",
                ") -> ChildCategory.ParentMethods:",
                "    return provider.normalized()",
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

    assert with_plugin.errors == [
        (
            f'{consumer_path}:7: note: Revealed type is '
            '"fixtures.self_type.ChildCategory.ParentMethods"'
        ),
        (
            f'{consumer_path}:13: error: Incompatible return value type '
            '(got "fixtures.self_type.BaseCategory.ParentMethods", '
            'expected "fixtures.self_type.ChildCategory.ParentMethods")  '
            "[return-value]"
        ),
    ]
    assert any("[attr-defined]" in error for error in without_plugin.errors)


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


def _sets_subobjects_manifest() -> ProjectionManifest:
    base_manifest = _sets_cartesian_products_manifest()
    return base_manifest.model_copy(
        update={
            "projections": (
                *base_manifest.projections,
                ProviderProjection(
                    provider=(
                        "sage.categories.sets_cat."
                        "Sets.Subobjects.ParentMethods"
                    ),
                    role="parent",
                    runtime_class=(
                        "sage.categories.sets_cat.Sets.Subobjects.parent_class"
                    ),
                    runtime_bases=(
                        "sage.categories.sets_cat.Sets.Subquotients.parent_class",
                    ),
                    runtime_mro=(
                        "sage.categories.sets_cat.Sets.Subobjects.parent_class",
                        "sage.categories.sets_cat.Sets.Subquotients.parent_class",
                        "sage.categories.sets_cat.Sets.parent_class",
                        "sage.categories.objects.Objects.parent_class",
                        "builtins.object",
                    ),
                    provider_bases=(
                        "sage.categories.sets_cat."
                        "Sets.Subquotients.ParentMethods",
                    ),
                    provider_mro=(
                        "sage.categories.sets_cat."
                        "Sets.Subobjects.ParentMethods",
                        "sage.categories.sets_cat."
                        "Sets.Subquotients.ParentMethods",
                        "sage.categories.sets_cat.Sets.ParentMethods",
                        "sage.categories.objects.Objects.ParentMethods",
                    ),
                ),
                ProviderProjection(
                    provider=(
                        "sage.categories.sets_cat."
                        "Sets.Subquotients.ParentMethods"
                    ),
                    role="parent",
                    runtime_class=(
                        "sage.categories.sets_cat.Sets.Subquotients.parent_class"
                    ),
                    runtime_bases=("sage.categories.sets_cat.Sets.parent_class",),
                    runtime_mro=(
                        "sage.categories.sets_cat.Sets.Subquotients.parent_class",
                        "sage.categories.sets_cat.Sets.parent_class",
                        "sage.categories.objects.Objects.parent_class",
                        "builtins.object",
                    ),
                    provider_bases=("sage.categories.sets_cat.Sets.ParentMethods",),
                    provider_mro=(
                        "sage.categories.sets_cat."
                        "Sets.Subquotients.ParentMethods",
                        "sage.categories.sets_cat.Sets.ParentMethods",
                        "sage.categories.objects.Objects.ParentMethods",
                    ),
                ),
            ),
        }
    )


def _self_return_provider_manifest() -> ProjectionManifest:
    return ProjectionManifest.model_validate(
        {
            "schema_version": 1,
            "generated_by": "tests",
            "sage_version": "10.7",
            "python_version": "3.12.13",
            "projections": (
                ProviderProjection(
                    provider="fixtures.self_type.BaseCategory.ParentMethods",
                    role="parent",
                    runtime_class="fixtures.self_type.BaseCategory.parent_class",
                    runtime_bases=("builtins.object",),
                    runtime_mro=(
                        "fixtures.self_type.BaseCategory.parent_class",
                        "builtins.object",
                    ),
                    provider_bases=(),
                    provider_mro=(
                        "fixtures.self_type.BaseCategory.ParentMethods",
                    ),
                ).model_dump(mode="json"),
                ProviderProjection(
                    provider="fixtures.self_type.ChildCategory.ParentMethods",
                    role="parent",
                    runtime_class="fixtures.self_type.ChildCategory.parent_class",
                    runtime_bases=(
                        "fixtures.self_type.BaseCategory.parent_class",
                    ),
                    runtime_mro=(
                        "fixtures.self_type.ChildCategory.parent_class",
                        "fixtures.self_type.BaseCategory.parent_class",
                        "builtins.object",
                    ),
                    provider_bases=(
                        "fixtures.self_type.BaseCategory.ParentMethods",
                    ),
                    provider_mro=(
                        "fixtures.self_type.ChildCategory.ParentMethods",
                        "fixtures.self_type.BaseCategory.ParentMethods",
                    ),
                ).model_dump(mode="json"),
            ),
            "source_modules": (
                SourceModuleRecord(
                    module="fixtures.self_type",
                    path="fixtures/self_type.py",
                    sha256="0" * 64,
                    mtime_ns=1_789_000_000_000_000_000,
                ).model_dump(mode="json"),
            ),
            "provider_methods": (
                {
                    "provider": "fixtures.self_type.BaseCategory.ParentMethods",
                    "name": "normalized",
                    "return_type": "Self",
                },
            ),
        }
    )


def _left_zero_semigroup_concrete_parent_manifest() -> ProjectionManifest:
    return ProjectionManifest(
        schema_version=1,
        generated_by="tests",
        sage_version="10.7",
        python_version="3.12.13",
        projections=(
            ProviderProjection(
                provider="sage.categories.semigroups.Semigroups.ParentMethods",
                role="parent",
                runtime_class="sage.categories.semigroups.Semigroups.parent_class",
                runtime_bases=("builtins.object",),
                runtime_mro=(
                    "sage.categories.semigroups.Semigroups.parent_class",
                    "builtins.object",
                ),
                provider_bases=(),
                provider_mro=("sage.categories.semigroups.Semigroups.ParentMethods",),
            ),
            ProviderProjection(
                provider="sage.categories.semigroups.Semigroups.ElementMethods",
                role="element",
                runtime_class="sage.categories.semigroups.Semigroups.element_class",
                runtime_bases=("builtins.object",),
                runtime_mro=(
                    "sage.categories.semigroups.Semigroups.element_class",
                    "builtins.object",
                ),
                provider_bases=(),
                provider_mro=("sage.categories.semigroups.Semigroups.ElementMethods",),
            ),
        ),
        source_modules=(
            SourceModuleRecord(
                module="sage.categories.semigroups",
                path="sage/categories/semigroups.py",
                sha256="0" * 64,
                mtime_ns=1_789_000_000_000_000_000,
            ),
            SourceModuleRecord(
                module="sage.categories.examples.semigroups",
                path="sage/categories/examples/semigroups.py",
                sha256="1" * 64,
                mtime_ns=1_789_000_000_000_000_001,
            ),
            SourceModuleRecord(
                module="sage.structure.element",
                path="sage/structure/element.pyx",
                sha256="2" * 64,
                mtime_ns=1_789_000_000_000_000_002,
            ),
        ),
        concrete_parents=(
            ConcreteParentRecord(
                concrete_class="sage.categories.examples.semigroups.LeftZeroSemigroup",
                runtime_class=(
                    "sage.categories.examples.semigroups."
                    "LeftZeroSemigroup_with_category"
                ),
                runtime_mro=(
                    "sage.categories.examples.semigroups."
                    "LeftZeroSemigroup_with_category",
                    "sage.categories.examples.semigroups.LeftZeroSemigroup",
                ),
                category_class="sage.categories.semigroups.Semigroups_with_category",
                parent_provider_mro=(
                    "sage.categories.semigroups.Semigroups.ParentMethods",
                ),
                element_runtime_class=(
                    "sage.categories.examples.semigroups."
                    "LeftZeroSemigroup_with_category.element_class"
                ),
                element_runtime_mro=(
                    "sage.categories.examples.semigroups."
                    "LeftZeroSemigroup_with_category.element_class",
                    "sage.structure.element.Element",
                ),
                element_provider_mro=(
                    "sage.categories.semigroups.Semigroups.ElementMethods",
                ),
            ),
        ),
        external_runtime_classes=(
            ExternalRuntimeClassRecord(
                runtime_class="sage.structure.element.Element",
                module="sage.structure.element",
                static_signature_source="untyped_external",
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
