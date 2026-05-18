from __future__ import annotations

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
from sage_mypy_category_plugin.projection import ProviderMethodRecord
from sage_mypy_category_plugin.projection import ProviderProjection
from sage_mypy_category_plugin import stubs as stubs_cli
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
                element_provider_mro=(
                    "sage.categories.semigroups.Semigroups.ElementMethods",
                ),
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
