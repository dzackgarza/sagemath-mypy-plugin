"""Axiom base imported from the parent package mirrors category_specs over_pid."""
from __future__ import annotations

from typing import override

from .. import Modules
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _OverPID(LocalCategoryBase):
    _base_category_class_and_axiom = (Modules, "OverPID")

    class ParentMethods:
        @override
        def is_over_pid(self) -> bool:
            return True
