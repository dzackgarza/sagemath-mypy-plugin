from typing import Any, Callable, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])


class AbstractMethod: ...


def abstract_method(func: _F, /, **kwargs: Any) -> _F: ...
