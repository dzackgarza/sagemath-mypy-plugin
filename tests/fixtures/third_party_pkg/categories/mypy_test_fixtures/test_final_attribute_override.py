"""Observed non-plugin failure: overriding a final class attribute."""

from typing import Final


class _FinalBase:
    Endset: Final[int] = 1


class _FinalSub(_FinalBase):
    Endset = 2
