"""Green-contributor-style Sage category with valid ParentMethods overrides."""

from typing import override as _override

from sage.categories.category import Category
from sage.misc.abstract_method import abstract_method


class ContributorModules(Category):
    """Barebones analogue of a Sage category such as ``Modules``."""

    def super_categories(self):
        return []

    @classmethod
    def an_instance(cls):
        return cls()

    class SubcategoryMethods:
        def Free(self):
            return ContributorFreeModules.an_instance()

    class ParentMethods:
        @abstract_method
        def basis_keys(self) -> tuple[str, ...]:
            raise NotImplementedError

        def rank(self) -> int:
            return len(self.basis_keys())

        def scale(self, scalar: int) -> str:
            return f"scaled by {scalar}"

        def coerce_key(self, key: object) -> str:
            return str(key)


class ContributorFreeModules(Category):
    def super_categories(self):
        return [ContributorModules.an_instance()]

    @classmethod
    def an_instance(cls):
        return cls()

    class ParentMethods:
        @_override
        def basis_keys(self) -> tuple[str, ...]:
            return ("e0", "e1")

        @_override
        def rank(self) -> int:
            return 2

        @_override
        def scale(self, scalar: int) -> str:
            return f"free-scaled by {scalar}"

        @_override
        def coerce_key(self, key: object) -> str:
            return f"free:{key}"
