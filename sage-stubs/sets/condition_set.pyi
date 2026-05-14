from collections.abc import Callable
from typing import Any

from sage.structure.parent import Parent


class ConditionSet(Parent):
    def __init__(
        self,
        ambient: Any,
        predicate: Callable[[Any], bool],
        *,
        category: Any = ...,
    ) -> None: ...
    def ambient(self) -> Any: ...

