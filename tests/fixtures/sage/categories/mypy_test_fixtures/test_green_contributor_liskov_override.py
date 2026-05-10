"""Invalid override: subcategory narrows an accepted parameter type."""

from typing import override as _override

from sage.categories.category import Category


class LiskovOverrideBase(Category):
    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        def coerce_key(self, key: object) -> str:
            return str(key)


class LiskovOverrideSubcategory(Category):
    def super_categories(self):
        return [LiskovOverrideBase.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def coerce_key(self, key: str) -> str:
            return key
