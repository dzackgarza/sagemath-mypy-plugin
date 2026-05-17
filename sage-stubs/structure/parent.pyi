from typing import Any

from .category_object import CategoryObject


class Parent(CategoryObject):
    Hom: Any

    def __init__(self: Any, category: Any = ...) -> None: ...
    def _refine_category_(self, category: Any) -> None: ...
    def _test_not_implemented_methods(self) -> None: ...
