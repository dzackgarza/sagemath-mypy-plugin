from __future__ import annotations

from importlib import import_module
from types import ModuleType


def import_fullname(fullname: str) -> object:
    module, qualname = import_module_and_qualname(fullname)
    current: object = module
    for name in qualname:
        if not hasattr(current, name):
            raise AttributeError(
                f"{fullname!r} references missing attribute {name!r} on {current!r}"
            )
        current = getattr(current, name)
    return current


def import_module_and_qualname(fullname: str) -> tuple[ModuleType, tuple[str, ...]]:
    parts = fullname.split(".")
    if len(parts) < 2:
        raise ValueError(f"Expected fully-qualified name, got {fullname!r}")

    for split_index in range(len(parts), 0, -1):
        module_name = ".".join(parts[:split_index])
        try:
            module = import_module(module_name)
        except ModuleNotFoundError as error:
            missing_name = error.name
            if missing_name is None or not (
                module_name == missing_name
                or module_name.startswith(f"{missing_name}.")
            ):
                raise
            continue
        return module, tuple(parts[split_index:])

    raise ModuleNotFoundError(f"Could not import any module prefix of {fullname!r}")


def importable_module_name_or_none(fullname: str) -> str | None:
    try:
        module, _ = import_module_and_qualname(fullname)
    except ModuleNotFoundError:
        return None
    return module.__name__


__all__ = [
    "import_fullname",
    "import_module_and_qualname",
    "importable_module_name_or_none",
]
