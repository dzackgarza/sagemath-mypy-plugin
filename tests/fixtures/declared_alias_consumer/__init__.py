"""Runtime category role aliases reported by their declaring compiler."""

from tests.fixtures.declared_alias_consumer.roles import AliasCategory

Role = AliasCategory().parent_class


class Compiler:
    def declared_inheritance(self) -> dict[str, dict[str, tuple[str, ...]]]:
        provider = AliasCategory.ParentMethods
        return {"object": {f"{provider.__module__}.{provider.__qualname__}": ()}}

    def declared_subtyping(self) -> dict[str, dict[str, tuple[str, ...]]]:
        return {}

    def declared_type_aliases(self) -> dict[str, str]:
        provider = AliasCategory.ParentMethods
        return {f"{__name__}.Role": f"{provider.__module__}.{provider.__qualname__}"}


compiler = Compiler()
