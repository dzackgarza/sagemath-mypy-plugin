"""Runtime category role aliases reported by their declaring compiler."""

from __future__ import annotations

from importlib import import_module


def evaluate_role(value: Role[int]) -> int:
    return value.echo(7)


roles = import_module(f"{__name__}.roles")
Role: type[object] = roles.AliasCategory().parent_class


class Compiler:
    def declared_inheritance(self) -> dict[str, dict[str, tuple[str, ...]]]:
        provider = roles.AliasCategory.ParentMethods
        return {"object": {f"{provider.__module__}.{provider.__qualname__}": ()}}

    def declared_subtyping(self) -> dict[str, dict[str, tuple[str, ...]]]:
        return {}

    def declared_type_aliases(self) -> dict[str, str]:
        provider = roles.AliasCategory.ParentMethods
        return {f"{__name__}.Role": f"{provider.__module__}.{provider.__qualname__}"}


compiler = Compiler()
