from tests.fixtures.invariant_core.graph_mor_runtime import IsometryArrowMethods


def invalid_arrow_method(arrow: IsometryArrowMethods) -> int:
    return arrow.not_a_runtime_provider_method()
