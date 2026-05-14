"""Observed non-plugin failure: overriding a final instance method."""

from typing import final, override as _override


class _FinalBase:
    @final
    def extra_super_categories(self) -> list[int]:
        return [1]


class _FinalSub(_FinalBase):
    @_override
    def extra_super_categories(self) -> list[int]:
        return [2]
