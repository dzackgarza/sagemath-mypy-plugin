"""@final decorator propagation through method container assignment.

Mypy fires "@final cannot be used with non-method functions" when a module-level
helper is assigned as a method container alias and that helper uses @final.
The plugin must suppress this because the helper IS semantically a method.
"""
from typing import final

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


@final
def final_of(self) -> int:
    return 1


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class ParentMethods:
        def of(self, *args) -> int:
            return 0


class _LocalSub(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_LocalBase.an_instance()]

    @classmethod
    def an_instance(cls) -> "_LocalSub":
        return cls()

    class ParentMethods:
        of = final_of  # assigned helper — triggers [misc] without plugin
