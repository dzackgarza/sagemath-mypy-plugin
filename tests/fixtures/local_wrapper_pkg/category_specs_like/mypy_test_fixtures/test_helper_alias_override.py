"""Valid helper-alias @override in a local-wrapper hierarchy.

The category directly assigns its ParentMethods to a standalone helper class
via ``ParentMethods = _HelperParentMethods``. Methods on the helper use
@override to override methods from the base category's ParentMethods. The
plugin must resolve the override through the alias chain.  The helper class
name must end in ``Methods`` so that ``_looks_like_method_container`` triggers
the MRO hook.
"""
from typing import override as _override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class ParentMethods:
        def compute(self) -> int:
            return 0

        def is_finite(self) -> bool:
            return True


class _HelperParentMethods:
    """Standalone helper class assigned as ParentMethods alias."""

    @_override
    def compute(self) -> int:
        return 1

    def is_finite(self) -> bool:
        return False


class _LocalSub(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return [_LocalBase.an_instance()]

    @classmethod
    def an_instance(cls) -> "_LocalSub":
        return cls()

    ParentMethods = _HelperParentMethods
