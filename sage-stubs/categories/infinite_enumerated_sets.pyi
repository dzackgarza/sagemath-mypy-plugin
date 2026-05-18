from typing import Any

from sage.categories.enumerated_sets import EnumeratedSets


class InfiniteEnumeratedSets(EnumeratedSets):
    class ParentMethods:
        def random_element(self) -> Any: ...
