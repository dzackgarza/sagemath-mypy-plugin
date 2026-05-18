from __future__ import annotations

from typing import Any, cast

import sage.all  # type: ignore[import-untyped] # noqa: F401
from sage.categories.category import Category as _SageCategory  # type: ignore[import-untyped]
from sage.categories.category_singleton import (  # type: ignore[import-untyped]
    Category_singleton as _SageCategorySingleton,
)
from sage.misc.constant_function import ConstantFunction  # type: ignore[import-untyped]
from sage.structure.dynamic_class import DynamicMetaclass  # type: ignore[import-untyped]


class Category(_SageCategory):
    @classmethod
    def an_instance(cls) -> Category:
        return cls()


class _SingletonClasscallMixin:
    @staticmethod
    def __classcall__(cls: type[_SageCategorySingleton]) -> Category:
        if isinstance(cls, DynamicMetaclass):
            cls = cls.__base__
        obj = cast(Any, super(_SageCategorySingleton, cls)).__classcall__(cls)
        cls._set_classcall(ConstantFunction(obj))
        obj.__class__._set_classcall(ConstantFunction(obj))
        return cast(Category, obj)


class Category_singleton(_SingletonClasscallMixin, _SageCategorySingleton):
    @classmethod
    def an_instance(cls) -> Category_singleton:
        return cls()
