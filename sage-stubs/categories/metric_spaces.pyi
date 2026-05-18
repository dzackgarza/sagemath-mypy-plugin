from sage.categories.category import Category


class MetricSpaces(Category):
    class ParentMethods:
        def is_metric(self) -> bool: ...
