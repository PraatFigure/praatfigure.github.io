from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True, slots=True)
class Annotation:
    index: int
    start: float
    end: float | None
    label: str

    @property
    def is_point(self) -> bool:
        return self.end is None

    @property
    def duration(self) -> float:
        return 0.0 if self.end is None else self.end - self.start


@dataclass(slots=True)
class Tier:
    name: str
    kind: Literal["interval", "point"]
    entries: list[Annotation] = field(default_factory=list)
    display_name: str | None = None

    @property
    def non_empty(self) -> bool:
        return any(entry.label.strip() for entry in self.entries)

    def search(self, query: str, mode: Literal["contains", "exact", "regex"] = "contains",
               case_sensitive: bool = False) -> list[Annotation]:
        import re
        if not case_sensitive:
            query_cmp = query.casefold()
        else:
            query_cmp = query
        result: list[Annotation] = []
        pattern = re.compile(query, 0 if case_sensitive else re.IGNORECASE) if mode == "regex" else None
        for entry in self.entries:
            label = entry.label if case_sensitive else entry.label.casefold()
            matches = (
                query_cmp in label if mode == "contains" else
                query_cmp == label if mode == "exact" else
                bool(pattern.search(entry.label))
            )
            if matches:
                result.append(entry)
        return result

    def containing(self, timestamp: float) -> Annotation | None:
        for entry in self.entries:
            if entry.end is not None and entry.start <= timestamp <= entry.end:
                return entry
        return None


@dataclass(slots=True)
class TextGridDocument:
    xmin: float
    xmax: float
    tiers: list[Tier]
    path: str | None = None

    def tier(self, name: str) -> Tier:
        for tier in self.tiers:
            if tier.name == name:
                return tier
        raise KeyError(f"Unknown tier: {name}")

