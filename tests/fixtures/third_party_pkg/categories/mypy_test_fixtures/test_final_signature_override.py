"""Observed non-plugin failure: final override with incompatible signature."""

from typing import final, override as _override


class _FinalBase:
    @final
    def Of(self, domain: int, codomain: int) -> int:
        return domain + codomain


class _FinalSub(_FinalBase):
    @_override
    def Of(self, domain: int) -> int:
        return domain
