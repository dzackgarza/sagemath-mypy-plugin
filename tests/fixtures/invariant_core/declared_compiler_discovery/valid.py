from __future__ import annotations


class BaseProvider:
    def inherited_value(self) -> int:
        return 1


class ValidDerivedProvider:
    def inherited_value(self) -> int:
        return super().inherited_value()
