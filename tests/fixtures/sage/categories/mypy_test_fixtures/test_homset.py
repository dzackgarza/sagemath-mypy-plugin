"""Test 6: Homsets override — HomsetSubcategory.ParentMethods.@override f.

HomsetBase has a Homsets nested category. HomsetSubcategory.Homsets
inherits from HomsetBase.Homsets, whose ParentMethods defines f().
"""

from typing import override as _override

from sage.categories.category import Category


class HomsetBaseHomsets(Category):
    """Nested Homsets category for HomsetBase."""

    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def f(self) -> int:
            """Ancestor Homsets ParentMethods method."""
            return 1


class HomsetBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    @classmethod
    def Homsets(cls):
        return HomsetBaseHomsets


class HomsetSubcategoryHomsets(Category):
    """Homsets category inheriting from HomsetBase.Homsets."""

    def super_categories(self):
        return [HomsetBase.Homsets().an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def f(self) -> int:
            """Valid @override — f is defined in _A6.Homsets().ParentMethods."""
            return 2


class _B6(Category):
    def super_categories(self):
        return [HomsetBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    @classmethod
    def Homsets(cls):
        return HomsetSubcategoryHomsets
