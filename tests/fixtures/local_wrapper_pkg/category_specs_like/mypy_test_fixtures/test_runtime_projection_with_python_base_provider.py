"""Runtime-projected containers also inherit methods from Python category bases."""
from typing import override

from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _RuntimeBaseCategory(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_RuntimeBaseCategory":
        return cls()

    class ParentMethods:
        def runtime_base_method(self) -> object:
            return object()


class _PythonConstructionBase(LocalCategoryBase):
    class ParentMethods:
        def __init_extra__(self) -> None:
            pass


class _ConstructionWithPythonBase(_PythonConstructionBase):
    def super_categories(self):  # type: ignore[override]
        return [_RuntimeBaseCategory.an_instance()]

    @classmethod
    def an_instance(cls) -> "_ConstructionWithPythonBase":
        return cls()

    class ParentMethods:
        @override
        def __init_extra__(self) -> None:
            pass
