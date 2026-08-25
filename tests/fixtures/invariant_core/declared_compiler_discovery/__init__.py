from __future__ import annotations

from tests.fixtures.invariant_core.declared_compiler_discovery.invalid import (
    InvalidDerivedProvider,
)
from tests.fixtures.invariant_core.declared_compiler_discovery.valid import (
    BaseProvider,
    ValidDerivedProvider,
)


def _fullname(value: type[object]) -> str:
    return f"{value.__module__}.{value.__qualname__}"


class FixtureCompiler:
    def declared_inheritance(self) -> dict[str, dict[str, tuple[str, ...]]]:
        base = _fullname(BaseProvider)
        return {
            "object": {
                _fullname(ValidDerivedProvider): (base,),
                _fullname(InvalidDerivedProvider): (base,),
            },
            "element": {},
            "arrow": {},
        }

    def declared_subtyping(self) -> dict[str, dict[str, tuple[str, ...]]]:
        return {"object": {}, "element": {}, "arrow": {}}


compiler = FixtureCompiler()


def AConstruction() -> object:
    raise AssertionError("mathematical constructors are not discovery probes")
