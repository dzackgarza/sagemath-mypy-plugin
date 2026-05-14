"""Third-party invalid override fixture outside ``sage.categories.*``."""

from typing import override as _override

from sage.categories.category import Category


class _ThirdPartyA2(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def f(self) -> int:
            return 1


class _ThirdPartyB2(Category):
    def super_categories(self):
        return [_ThirdPartyA2.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def g(self) -> int:
            return 2
