"""Constructors() called on a category instance must not produce [call-arg].

In category_specs, a class Constructors and a method Constructors are both
defined on the category class. At the call site `_LocalBase().Constructors()`,
mypy treats Constructors as the class (due to [no-redef] collapsing the name)
and fires [call-arg] because the class __init__ requires a positional `category`
argument. The plugin must recognise this as a valid zero-arg method call.
"""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class Constructors:
        """Constructor collector — requires category at init."""
        def __init__(self, category: "_LocalBase") -> None:
            self._category = category

        def primes(self) -> object:
            return object()

    _Constructors = Constructors

    def Constructors(self) -> "Constructors":  # [no-redef] fires here; [call-arg] at call sites
        return self.__class__._Constructors(self)  # type: ignore[attr-defined]


def build_primes() -> object:
    return _LocalBase.an_instance().Constructors().primes()  # [call-arg] without plugin
