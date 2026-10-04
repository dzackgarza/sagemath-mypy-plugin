from __future__ import annotations

from sage.categories.morphism import Morphism  # type: ignore[import-untyped]

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class LinearArrowMethods:
    def domain(self) -> int:
        return 1


class EmbeddingArrowMethods:
    def injective_witness(self) -> int:
        return 2


class IsometryArrowMethods:
    def invertible_witness(self) -> int:
        return 3


def _arrow_type(name: str, providers: tuple[type, ...]) -> type:
    return type(
        name,
        (*providers, Morphism),
        {"__module__": __name__, "__qualname__": name},
    )


class LinearMor:
    ElementMethods = LinearArrowMethods
    element_class = _arrow_type("LinearMor.ArrowType", (LinearArrowMethods,))


class EmbeddingMor:
    ElementMethods = EmbeddingArrowMethods
    element_class = _arrow_type(
        "EmbeddingMor.ArrowType",
        (EmbeddingArrowMethods, LinearArrowMethods),
    )


class IsometryMor:
    ElementMethods = IsometryArrowMethods
    element_class = _arrow_type(
        "IsometryMor.ArrowType",
        (IsometryArrowMethods, EmbeddingArrowMethods, LinearArrowMethods),
    )


class GraphMorCategory(LocalCategoryBase):
    def super_categories(self) -> list[LocalCategoryBase]:
        return []

    def an_object(self) -> object:
        return object()

    def Mor(self, source: object, target: object) -> LinearMor:
        return LinearMor()

    def Mono(self, source: object, target: object) -> EmbeddingMor:
        return EmbeddingMor()

    def Iso(self, source: object, target: object) -> IsometryMor:
        return IsometryMor()


class LiveGraphObject:
    def Mor(self, codomain: object) -> IsometryMor:
        del codomain
        return IsometryMor()


class LiveGraphCategory:
    class ParentMethods:
        def Mor(self, codomain: object) -> IsometryMor:
            raise AssertionError("fixture declaration only")

    @classmethod
    def an_instance(cls) -> LiveGraphCategory:
        return cls()

    def an_object(self) -> LiveGraphObject:
        return LiveGraphObject()
