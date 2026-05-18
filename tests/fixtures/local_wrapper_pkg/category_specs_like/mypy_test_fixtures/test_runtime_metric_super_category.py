"""Nested containers inherit methods from the runtime Sage metric category."""
from __future__ import annotations

from typing import override

from sage.categories.metric_spaces import MetricSpaces as SageMetricSpaces

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _LocalMetricSpaces(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [SageMetricSpaces()]

    @classmethod
    def an_instance(cls) -> "_LocalMetricSpaces":
        return cls()

    class ParentMethods:
        @override
        def is_metric(self) -> bool:
            return True
