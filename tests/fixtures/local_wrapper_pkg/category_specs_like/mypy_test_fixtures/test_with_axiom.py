"""SubcategoryMethods._with_axiom call in a local-wrapper hierarchy.

_with_axiom is a Sage Category method dynamically available on SubcategoryMethods.
The plugin must teach mypy that SubcategoryMethods has this attribute so that
calls like self._with_axiom("Gcd") do not produce [attr-defined] errors.
"""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class SubcategoryMethods:
        def gcd_domain(self) -> "_LocalBase":
            return self._with_axiom("Gcd")

        def unique_factorization_domain(self) -> "_LocalBase":
            return self._with_axiom("UniqueFactorization")
