from __future__ import annotations

from collections import OrderedDict
from typing import Callable, Hashable, TypeVar

T = TypeVar("T")


class AnalysisCache:
    """Small LRU cache; style changes never enter its acoustic keys."""

    def __init__(self, maximum_items: int = 32) -> None:
        self.maximum_items = maximum_items
        self._items: OrderedDict[Hashable, object] = OrderedDict()

    def get_or_create(self, key: Hashable, factory: Callable[[], T]) -> T:
        if key in self._items:
            self._items.move_to_end(key)
            return self._items[key]  # type: ignore[return-value]
        value = factory()
        self._items[key] = value
        while len(self._items) > self.maximum_items:
            self._items.popitem(last=False)
        return value

    def clear(self) -> None:
        self._items.clear()

