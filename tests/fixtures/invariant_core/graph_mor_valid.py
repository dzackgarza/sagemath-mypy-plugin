from tests.fixtures.invariant_core.graph_mor_runtime import (
    EmbeddingArrowMethods,
    IsometryArrowMethods,
)


def embedding_domain(arrow: EmbeddingArrowMethods) -> int:
    return arrow.domain()


def isometry_domain(arrow: IsometryArrowMethods) -> int:
    return arrow.domain()


def isometry_injective_witness(arrow: IsometryArrowMethods) -> int:
    return arrow.injective_witness()
