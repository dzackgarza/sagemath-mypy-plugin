from collections.abc import Callable
from typing import Any

from sage.structure.parent import Parent


class ConditionSet(Parent):
    def __init__(
        self,
        ambient: Any,
        predicate: Callable[[Any], bool],
        *predicates: Callable[[Any], bool],
        names: str | tuple[str, ...] | None = ...,
        category: Any = ...,
    ) -> None: ...
    def ambient(self) -> Any: ...
