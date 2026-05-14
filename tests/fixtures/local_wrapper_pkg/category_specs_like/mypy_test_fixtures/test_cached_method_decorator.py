"""@cached_method decorator must not make the decorated function untyped.

An untyped decorator (no annotations) triggers [untyped-decorator] and makes
the return type of the decorated function Any. The plugin/stubs must provide a
typed signature for @cached_method so that decorated functions remain typed.
"""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


def untyped_cached_method(f):  # no type annotations — triggers [untyped-decorator]
    return f


class _LocalBase(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_LocalBase":
        return cls()

    class SubcategoryMethods:
        @untyped_cached_method
        def finite(self) -> "_LocalBase":
            return _LocalBase.an_instance()

        @untyped_cached_method
        def countable(self) -> "_LocalBase":
            return _LocalBase.an_instance()
