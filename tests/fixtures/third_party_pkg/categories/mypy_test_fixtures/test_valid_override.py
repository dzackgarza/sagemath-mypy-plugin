"""Third-party valid override fixture outside ``sage.categories.*``."""

from typing import override as _override

from sage.categories.category import Category


class _ThirdPartyA(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def f(self) -> int:
            return 1


class _ThirdPartyB(Category):
    def super_categories(self):
        return [_ThirdPartyA.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def f(self) -> int:
            return 2
