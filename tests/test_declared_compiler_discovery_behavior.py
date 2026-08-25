from __future__ import annotations

from sage_mypy_category_plugin.declared import (
    compiler_in,
    declared_projections,
)
from tests.fixtures.invariant_core.declared_compiler_discovery import (
    compiler,
)
from tests.fixtures.invariant_core.declared_compiler_discovery.invalid import (
    InvalidDerivedProvider,
)
from tests.fixtures.invariant_core.declared_compiler_discovery.valid import (
    BaseProvider,
    ValidDerivedProvider,
)

PACKAGE = "tests.fixtures.invariant_core.declared_compiler_discovery"


def _fullname(value: type[object]) -> str:
    return f"{value.__module__}.{value.__qualname__}"


def test_declared_compiler_discovery_precedes_constructor_probes() -> None:
    assert compiler_in((PACKAGE,)) is compiler

    projections = {
        projection.provider: projection
        for projection in declared_projections((PACKAGE,), ("parent",))
    }
    base = _fullname(BaseProvider)
    valid = projections[_fullname(ValidDerivedProvider)]
    invalid = projections[_fullname(InvalidDerivedProvider)]

    assert valid.provider_bases == (base,)
    assert invalid.provider_bases == (base,)
    assert projections[base].provider_bases == ()
