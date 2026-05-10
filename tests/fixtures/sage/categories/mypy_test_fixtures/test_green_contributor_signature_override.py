"""Invalid override: subcategory drops a required super-method argument."""

from typing import override as _override

from sage.categories.category import Category


class SignatureOverrideBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def scale(self, scalar: int) -> str:
            return f"scaled by {scalar}"


class SignatureOverrideSubcategory(Category):
    def super_categories(self):
        return [SignatureOverrideBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def scale(self) -> str:
            return "scaled"
