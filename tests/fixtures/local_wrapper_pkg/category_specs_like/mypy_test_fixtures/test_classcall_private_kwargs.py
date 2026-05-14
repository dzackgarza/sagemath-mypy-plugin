"""Keyword args declared on __classcall_private__ must be accepted at the call site.

In category_specs, Modules(base_ring, dispatch=False) is the canonical form.
The dispatch= kwarg is declared on __classcall_private__, not __init__.
mypy only looks at __init__ for call-site checking, so it fires [call-arg] for
the dispatch=False argument. The plugin must surface __classcall_private__ kwargs.
"""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _ParameterisedCategory(LocalCategoryBase):
    """Category whose public constructor accepts a dispatch kwarg via __classcall_private__."""

    def __init__(self, base_category: "_LocalBase") -> None:
        # __init__ does NOT declare dispatch — only __classcall_private__ does.
        pass

    @classmethod
    def an_instance(cls) -> "_ParameterisedCategory":
        return cls(_LocalBase.an_instance())

    class ParentMethods:
        pass


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class SubcategoryMethods:
        def undispatched(self) -> _ParameterisedCategory:
            base = _LocalBase.an_instance()
            return _ParameterisedCategory(base, dispatch=False)  # [call-arg] without plugin
