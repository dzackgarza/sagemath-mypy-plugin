from __future__ import annotations

from pathlib import Path

_PACKAGE_MARKERS = (
    Path("sage/__init__.pyi"),
    Path("sage/categories/__init__.pyi"),
    Path("sage/structure/__init__.pyi"),
    Path("sage/misc/__init__.pyi"),
    Path("sage/sets/__init__.pyi"),
    Path("sage/matrix/__init__.pyi"),
    Path("sage/rings/__init__.pyi"),
    Path("sage/rings/polynomial/__init__.pyi"),
    Path("sage/combinat/__init__.pyi"),
    Path("sage/combinat/posets/__init__.pyi"),
)

_STUB_SOURCES: dict[Path, str] = {
    Path("sage/categories/category.pyi"): (
        "from collections.abc import Sequence\n"
        "from typing import Any\n"
        "\n"
        "class Category:\n"
        "    parent_class: type\n"
        "    Constructors: Any\n"
        "    def __init__(self, *args: Any, **kwargs: Any) -> None: ...\n"
        "    @classmethod\n"
        "    def join(cls, categories: Any) -> 'Category': ...\n"
        "    @classmethod\n"
        "    def meet(cls, categories: Any) -> 'Category': ...\n"
        "    @classmethod\n"
        "    def __classcall__(cls, *args: Any, **kwargs: Any) -> Any: ...\n"
        "    @classmethod\n"
        "    def _set_classcall(cls, value: Any) -> None: ...\n"
        "    def super_categories(self) -> Any: ...\n"
        "    def extra_super_categories(self) -> Sequence['Category']: ...\n"
        "    def is_subcategory(self, other: Any) -> bool: ...\n"
        "    def Hom(self, codomain: Any) -> Any: ...\n"
        "    def HomCategory(self) -> Any: ...\n"
        "    def EndCategory(self) -> Any: ...\n"
        "    def AutCategory(self) -> Any: ...\n"
        "    def base_category(self: Any) -> 'Category': ...\n"
        "    def Of(self, *args: Any, **kwargs: Any) -> Any: ...\n"
        "    def _with_axiom(self: Any, axiom: str) -> Any: ...\n"
        "    def _make_named_class(\n"
        "        self: Any,\n"
        "        name: Any,\n"
        "        method_provider: Any,\n"
        "        cache: bool = ...,\n"
        "        picklable: bool = ...,\n"
        "    ) -> type: ...\n"
        "    def _repr_object_names(self) -> str: ...\n"
        "    def __contains__(self, candidate: Any) -> bool: ...\n"
        "\n"
        "class CategoryWithParameters(Category): ...\n"
        "class JoinCategory(Category): ...\n"
    ),
    Path("sage/categories/category_with_axiom.pyi"): (
        "from .category import Category\n"
        "\n"
        "from typing import Any\n"
        "\n"
        "class CategoryWithAxiom(Category):\n"
        "    def ambient_category(self) -> Category: ...\n"
        "    def defining_predicates(self) -> tuple[str, ...]: ...\n"
        "    def defining_predicate(self, candidate: Any) -> bool: ...\n"
        "class CategoryWithAxiom_over_base_ring(CategoryWithAxiom): ...\n"
        "class CategoryWithAxiom_singleton(CategoryWithAxiom): ...\n"
        "\n"
        "all_axioms: tuple[str, ...]\n"
    ),
    Path("sage/categories/cartesian_product.pyi"): (
        "from typing import Any\n"
        "\n"
        "from .category import Category\n"
        "\n"
        "class CartesianProductFunctor: ...\n"
        "\n"
        "class CartesianProductsCategory(Category):\n"
        "    @classmethod\n"
        "    def category_of(cls, category: Category, *args: Any, **kwargs: Any) -> Category: ...\n"
        "    def base_category(self) -> Any: ...\n"
        "    def extra_super_categories(self) -> Any: ...\n"
        "    class ParentMethods:\n"
        "        def __init_extra__(self) -> None: ...\n"
        "\n"
        "class _CartesianProductCallable:\n"
        "    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...\n"
        "    def category_from_parents(self, parents: Any) -> Any: ...\n"
        "\n"
        "cartesian_product: _CartesianProductCallable\n"
    ),
    Path("sage/categories/functor.pyi"): (
        "from typing import Any\n"
        "\n"
        "class Functor:\n"
        "    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...\n"
    ),
    Path("sage/categories/homset.pyi"): (
        "from typing import Any\n"
        "\n"
        "class Homset:\n"
        "    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...\n"
    ),
    Path("sage/categories/morphism.pyi"): (
        "from typing import Any\n"
        "\n"
        "class Morphism:\n"
        "    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...\n"
        "    def is_invertible(self) -> bool: ...\n"
    ),
    Path("sage/misc/abstract_method.pyi"): (
        "from typing import Any, Callable, TypeVar\n"
        "\n"
        "_F = TypeVar('_F', bound=Callable[..., Any])\n"
        "\n"
        "class AbstractMethod: ...\n"
        "\n"
        "def abstract_method(func: _F, /, **kwargs: Any) -> _F: ...\n"
    ),
    Path("sage/misc/cachefunc.pyi"): (
        "from typing import Any, Callable, TypeVar\n"
        "\n"
        "_F = TypeVar('_F', bound=Callable[..., Any])\n"
        "\n"
        "def cached_method(func: _F) -> _F: ...\n"
    ),
    Path("sage/misc/lazy_import.pyi"): (
        "from typing import Any\n"
        "\n"
        "class LazyImport:\n"
        "    def __init__(self, module: str, name: str, **kwargs: Any) -> None: ...\n"
        "    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...\n"
    ),
    Path("sage/sets/condition_set.pyi"): (
        "from collections.abc import Callable\n"
        "from typing import Any\n"
        "\n"
        "from sage.structure.parent import Parent\n"
        "\n"
        "class ConditionSet(Parent):\n"
        "    def __init__(\n"
        "        self,\n"
        "        ambient: Any,\n"
        "        predicate: Callable[[Any], bool],\n"
        "        *,\n"
        "        category: Any = ...,\n"
        "        names: Any = ...,\n"
        "    ) -> None: ...\n"
        "    def ambient(self) -> Any: ...\n"
    ),
    Path("sage/structure/category_object.pyi"): (
        "from typing import Any\n"
        "\n"
        "class CategoryObject:\n"
        "    def category(self) -> Any: ...\n"
        "    def _init_category_(self: Any, category: Any) -> None: ...\n"
    ),
    Path("sage/structure/element.pyi"): (
        "class Element:\n"
        "    ...\n"
    ),
    Path("sage/structure/parent.pyi"): (
        "from typing import Any\n"
        "\n"
        "from .category_object import CategoryObject\n"
        "\n"
        "class Parent(CategoryObject):\n"
        "    def __init__(self: Any, category: Any = ...) -> None: ...\n"
        "    def Hom(self: Any, *args: Any, **kwargs: Any) -> Any: ...\n"
        "    def _refine_category_(self, category: Any) -> None: ...\n"
        "    def _test_not_implemented_methods(self) -> None: ...\n"
        "    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...\n"
        "    def structure_morphism(self) -> Any: ...\n"
        "    def saturation(self, *args: Any, **kwargs: Any) -> Any: ...\n"
        "    def zero(self) -> Any: ...\n"
        "    def base_ring(self) -> Any: ...\n"
        "    def quotient_module(self, *args: Any, **kwargs: Any) -> Any: ...\n"
        "    def direct_sum(self, *args: Any, **kwargs: Any) -> Any: ...\n"
        "    def algebra(self, *args: Any, **kwargs: Any) -> Any: ...\n"
    ),
    Path("sage/matrix/matrix2.pyi"): (
        "from typing import Any\n"
        "\n"
        "class Matrix:\n"
        "    def subdivisions(self) -> Any: ...\n"
    ),
    Path("sage/rings/real_mpfi.pyi"): (
        "from typing import Any\n"
        "\n"
        "class RealIntervalField:\n"
        "    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...\n"
    ),
    Path("sage/rings/polynomial/ore_polynomial_ring.pyi"): (
        "from typing import Any\n"
        "\n"
        "class OrePolynomialRing:\n"
        "    def completion(self, *args: Any, **kwargs: Any) -> Any: ...\n"
    ),
    Path("sage/combinat/posets/posets.pyi"): (
        "class FinitePoset:\n"
        "    def is_meet_semilattice(self) -> bool: ...\n"
        "    def is_join_semilattice(self) -> bool: ...\n"
    ),
}


def static_stub_sources() -> dict[Path, str]:
    sources: dict[Path, str] = {path: "" for path in _PACKAGE_MARKERS}
    sources.update(_STUB_SOURCES)
    return dict(sorted(sources.items()))


def static_stub_modules() -> tuple[str, ...]:
    return tuple(
        ".".join(relative_path.with_suffix("").parts)
        for relative_path in static_stub_sources()
        if relative_path.name != "__init__.pyi"
    )
