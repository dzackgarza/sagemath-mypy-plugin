from typing import Any

from sage.structure.parent import Parent


class _FreeModuleReceiverMethods(Parent):
    def base_ring(self) -> Any: ...
    def basis(self) -> Any: ...
    def rank(self) -> Any: ...
    def dimension(self) -> Any: ...


class FreeModule_generic(_FreeModuleReceiverMethods): ...


def FreeModule(
    base_ring: Any,
    rank: Any,
    *args: Any,
    **kwargs: Any,
) -> FreeModule_generic: ...
