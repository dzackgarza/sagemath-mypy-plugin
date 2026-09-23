"""Consumer whose method containers are bases of the named classes they feed.

Sage's `Category._make_named_class` copies a container's `__dict__` into the
named class and warns when the container has a base class. A consumer can
instead put the container itself into the named class's bases, so that the
container's own base (here `Element`) and zero-argument `super()` are part of
the runtime MRO. The research preamble's `OwnedCategoryMixin` does this.
"""

from __future__ import annotations

import sage.all  # type: ignore[import-untyped]  # noqa: F401
from sage.categories.category import Category  # type: ignore[import-untyped]
from sage.categories.sets_cat import Sets  # type: ignore[import-untyped]
from sage.structure.dynamic_class import dynamic_class  # type: ignore[import-untyped]
from sage.structure.element import Element  # type: ignore[import-untyped]
from sage.structure.parent import Parent  # type: ignore[import-untyped]

from tests.fixtures.invariant_core.local_wrapper import LocalCategoryBase


class ContainerBasesCategory(LocalCategoryBase):
    """Local wrapper: the element container is a base of `element_class`."""

    def _make_named_class(
        self,
        name: str,
        method_provider: str,
        cache: bool = False,
        picklable: bool = True,
    ) -> type:
        if name != "element_class":
            return super()._make_named_class(  # type: ignore[no-any-return]
                name, method_provider, cache=cache, picklable=picklable
            )
        # Sage instantiates `<Category>_with_category`; the category class is next.
        declaring_class = type(self).__mro__[1]
        container = declaring_class.__dict__[method_provider]
        supers = tuple(
            category.element_class for category in self._super_categories_for_classes
        )
        named = dynamic_class(
            f"{declaring_class.__name__}.{name}", (container, *supers), cache=False
        )
        named.__qualname__ = f"{declaring_class.__qualname__}.{name}"
        named.__module__ = declaring_class.__module__
        return named


class PointedSets(ContainerBasesCategory):
    """Sets with a chosen base point."""

    def super_categories(self) -> list[Category]:
        return [Sets()]

    class ElementMethods(Element):
        def ambient_parent(self) -> Parent:
            return self.parent()
