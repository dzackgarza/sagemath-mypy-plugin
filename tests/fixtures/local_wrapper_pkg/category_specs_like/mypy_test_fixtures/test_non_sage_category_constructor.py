"""Ordinary classes named *Category must not receive Sage call rewriting."""


class _OrdinaryCategory:
    def __init__(self, category: object) -> None:
        self.category = category


def build_ordinary() -> _OrdinaryCategory:
    return _OrdinaryCategory()
