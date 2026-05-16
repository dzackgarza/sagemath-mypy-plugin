"""Type aliases consumed by the value-dependent completion fixture."""
from typing import Protocol

from .test_value_dependent_completion_self_return import _CompleteRings


class Ideal(Protocol):
    def is_zero(self) -> bool: ...


type CompleteRing = _CompleteRings.ParentMethods
