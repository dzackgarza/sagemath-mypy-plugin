"""Objects built by calling a category, as a research session builds them."""

from __future__ import annotations

from tests.fixtures.callable_parent_consumer import PointedSets


def base_point_of(data: int) -> object:
    return PointedSets()(data).base_point()


def undefined_method_of(data: int) -> object:
    return PointedSets()(data).cardinality_of_the_base_point()
