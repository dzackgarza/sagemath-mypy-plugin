from typing import Any


class LazyImport:
    def __init__(self, module: str, name: str) -> None: ...
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

