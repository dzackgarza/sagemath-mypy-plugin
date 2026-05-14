"""Covariant narrowing of method container class attributes in a local-wrapper hierarchy.

In Sage's category system, a specialised homset category narrows the type of
ParentMethods and ElementMethods by assigning a more specific class:

    class GenericHom(LocalCategoryBase):
        class ParentMethods: ...
        class ElementMethods: ...

    class SpecialHom(GenericHom):
        ParentMethods = _SpecialParentMethods   # narrowing assignment
        ElementMethods = _SpecialElementMethods  # narrowing assignment

Mypy fires [assignment] for these because class attributes are invariant by default.
The plugin must recognise method container assignments as valid covariant narrowing.
"""
from local_wrapper_pkg.category_specs_like.base_types import LocalCategoryBase


class _SpecialParentMethods:
    def hom_specific_method(self) -> int:
        return 0


class _SpecialElementMethods:
    def morphism_specific_method(self) -> bool:
        return True


class _GenericHomCategory(LocalCategoryBase):
    def super_categories(self):  # type: ignore[override]
        return []

    @classmethod
    def an_instance(cls) -> "_GenericHomCategory":
        return cls()

    class ParentMethods:
        pass

    class ElementMethods:
        pass


class _SpecialHomCategory(_GenericHomCategory):
    ParentMethods = _SpecialParentMethods    # covariant narrowing — must not be [assignment]
    ElementMethods = _SpecialElementMethods  # covariant narrowing — must not be [assignment]
