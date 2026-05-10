"""Invalid override: method is not present on the semantic supercategory."""

from typing import override as _override

from sage.categories.category import Category


class MissingOverrideBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def existing_method(self) -> int:
            return 1


class MissingOverrideSubcategory(Category):
    def super_categories(self):
        return [MissingOverrideBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def invented_method(self) -> int:
            return 2
