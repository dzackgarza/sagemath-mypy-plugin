"""Post-bound ParentMethods overloads should support override checking."""

from typing import overload, override as _override

from sage.categories.category import Category


@overload
def _helper(self: object, x: int) -> int: ...


@overload
def _helper(self: object, x: str) -> str: ...


def _helper(self: object, x: int | str) -> int | str:
    return x


class _PostbindOverloadBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        pass


_PostbindOverloadBase.ParentMethods.method = _helper


class _PostbindOverloadSub(Category):
    def super_categories(self):
        return [_PostbindOverloadBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @overload
        @_override
        def method(self, x: int) -> int: ...

        @overload
        @_override
        def method(self, x: str) -> str: ...

        @_override
        def method(self, x: int | str) -> int | str:
            return x
