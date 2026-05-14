from typing import Any

from .category_object import CategoryObject


class Parent(CategoryObject):
    @staticmethod
    def Hom(domain: Any, codomain: Any, *, category: Any = ...) -> Any: ...
    def _refine_category_(self, category: Any) -> None: ...
    def _test_not_implemented_methods(self) -> None: ...
