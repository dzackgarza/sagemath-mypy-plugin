"""Observed non-plugin failure: overriding a final classmethod."""

from typing import final, override as _override


class _FinalBase:
    @classmethod
    @final
    def default_super_categories(cls) -> list[int]:
        return [1]


class _FinalSub(_FinalBase):
    @classmethod
    @_override
    def default_super_categories(cls) -> list[int]:
        return [2]
