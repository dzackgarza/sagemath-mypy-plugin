from collections.abc import Callable, Iterator
from typing import Any

from sage.structure.parent import Parent


class _ImageSubobjectReceiverMethods(Parent):
    def __iter__(self) -> Iterator[Any]: ...
    def _an_element_(self) -> Any: ...


class ImageSubobject(_ImageSubobjectReceiverMethods):
    def __init__(
        self,
        function: Callable[..., Any],
        domain: Any,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...
