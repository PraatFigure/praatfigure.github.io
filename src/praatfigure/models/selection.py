from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

TimeMode = Literal["absolute", "relative_to_view_start", "relative_to_target_start"]


@dataclass(frozen=True, slots=True)
class TimeRange:
    start: float
    end: float

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("Time range end must be greater than start")

    @property
    def duration(self) -> float:
        return self.end - self.start

    def padded(self, left: float, right: float, *, minimum: float | None = None,
               maximum: float | None = None) -> "TimeRange":
        start = self.start - max(0.0, left)
        end = self.end + max(0.0, right)
        if minimum is not None:
            start = max(minimum, start)
        if maximum is not None:
            end = min(maximum, end)
        return TimeRange(start, end)


@dataclass(frozen=True, slots=True)
class Target:
    start: float
    end: float
    tier: str = ""
    entry_index: int | None = None
    label: str = ""
    display_label: str | None = None

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("Target end must be greater than start")

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TimeTransform:
    mode: TimeMode
    view_start: float
    target_start: float | None = None

    @property
    def origin(self) -> float:
        if self.mode == "absolute":
            return 0.0
        if self.mode == "relative_to_view_start":
            return self.view_start
        if self.target_start is None:
            raise ValueError("relative_to_target_start requires a target")
        return self.target_start

    def forward(self, value):
        return value - self.origin

    def inverse(self, value):
        return value + self.origin

