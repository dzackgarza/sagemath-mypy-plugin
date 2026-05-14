from .category import Category


class Homsets(Category):
    def Endset(self) -> Category: ...
    def Autset(self) -> Category: ...

