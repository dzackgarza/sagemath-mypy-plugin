from typing import Any

from sage.categories.enumerated_sets import EnumeratedSets


class FiniteEnumeratedSets(EnumeratedSets):
    class ParentMethods:
        def __len__(self) -> int: ...
        def cardinality(self) -> Any: ...
        def random_element(self) -> Any: ...
