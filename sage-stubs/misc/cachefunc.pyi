from typing import Any, Callable, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])


def cached_method(func: _F) -> _F: ...

