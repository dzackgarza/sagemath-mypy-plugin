"""A native alias whose target role is inherited, as in projected stubs."""

from .roles import AliasCategory


class InheritedCategory(AliasCategory):
    pass


type NativeRole[T = int] = InheritedCategory.ParentMethods[T]
