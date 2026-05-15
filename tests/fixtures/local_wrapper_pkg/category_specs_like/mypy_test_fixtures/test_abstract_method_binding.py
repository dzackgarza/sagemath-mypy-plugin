"""@abstractmethod propagation through method container assignment.

Mypy fires '"abstractmethod" used with a non-method' when a module-level
helper decorated with @abstractmethod is assigned as a method container alias.
The plugin must suppress this because the helper IS semantically a method.
"""
from abc import abstractmethod

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


@abstractmethod
def abstract_compute(self) -> int:
    ...


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class ParentMethods:
        def compute(self, *args) -> int:
            return 0


class _LocalSub(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_LocalBase.an_instance()]

    @classmethod
    def an_instance(cls) -> "_LocalSub":
        return cls()

    class ParentMethods:
        compute = abstract_compute  # assigned helper — triggers [misc] without plugin
