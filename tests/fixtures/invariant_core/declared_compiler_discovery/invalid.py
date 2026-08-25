from __future__ import annotations


class InvalidDerivedProvider:
    def inherited_value(self) -> str:
        return super().inherited_value()
