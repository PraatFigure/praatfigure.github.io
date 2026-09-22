from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .selection import Target, TimeMode, TimeRange
from .tracks import AnnotationTrack, SpectrogramTrack, Track, WaveformTrack, track_from_dict


@dataclass(slots=True)
class Appearance:
    width_mm: float = 160.0
    base_font_size: float = 9.0
    annotation_font_size: float = 10.0
    axis_font_size: float = 6.0
    font_family: str = "DejaVu Sans"
    foreground: str = "#111111"
    background: str = "#ffffff"
    panel_spacing: float = 0.0
    dpi: int = 150


@dataclass(slots=True)
class BoundaryProjection:
    mode: str = "target_only"
    tiers: list[str] = field(default_factory=list)
    merge: bool = True
    tolerance: float = 0.0005
    line_width: float = 1.1
    line_style: str = ":"
    opacity: float = 0.7
    label_target_times: bool = False
    target_time_decimals: int = 3


@dataclass(slots=True)
class DurationStyle:
    visible: bool = False
    unit: str = "auto"
    decimals: int = 0


@dataclass(slots=True)
class FigureSpec:
    view_range: TimeRange
    targets: list[Target] = field(default_factory=list)
    time_mode: TimeMode = "relative_to_view_start"
    tracks: list[Track] = field(default_factory=lambda: [WaveformTrack(), SpectrogramTrack()])
    boundary_projection: BoundaryProjection = field(default_factory=BoundaryProjection)
    duration: DurationStyle = field(default_factory=DurationStyle)
    appearance: Appearance = field(default_factory=Appearance)
    show_x_axis: bool = True
    x_ticks_mode: str = "endpoints"
    show_time_label: bool = False

    def validate(self) -> None:
        for target in self.targets:
            if target.start < self.view_range.start or target.end > self.view_range.end:
                raise ValueError("Every target must lie inside the view range")
        if self.time_mode == "relative_to_target_start" and not self.targets:
            raise ValueError("Target-zero time mode requires at least one target")
        if not any(track.visible for track in self.tracks):
            raise ValueError("At least one track must be visible")

    def to_dict(self) -> dict:
        return {
            "view_range": asdict(self.view_range),
            "targets": [target.to_dict() for target in self.targets],
            "time_mode": self.time_mode,
            "tracks": [track.to_dict() for track in self.tracks],
            "boundary_projection": asdict(self.boundary_projection),
            "duration": asdict(self.duration),
            "appearance": asdict(self.appearance),
            "show_x_axis": self.show_x_axis,
            "x_ticks_mode": self.x_ticks_mode,
            "show_time_label": self.show_time_label,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FigureSpec":
        return cls(
            view_range=TimeRange(**data["view_range"]),
            targets=[Target(**item) for item in data.get("targets", [])],
            time_mode=data.get("time_mode", "relative_to_view_start"),
            tracks=[track_from_dict(item) for item in data.get("tracks", [])],
            boundary_projection=BoundaryProjection(**data.get("boundary_projection", {})),
            duration=DurationStyle(**data.get("duration", {})),
            appearance=Appearance(**data.get("appearance", {})),
            show_x_axis=data.get("show_x_axis", True),
            x_ticks_mode=data.get("x_ticks_mode", "endpoints"),
            show_time_label=data.get("show_time_label", False),
        )

    @classmethod
    def publication(cls, view_range: TimeRange, targets: list[Target],
                    tiers: list[str]) -> "FigureSpec":
        return cls(
            view_range=view_range,
            targets=targets,
            tracks=[WaveformTrack(), SpectrogramTrack()] +
                   [AnnotationTrack(tier=name) for name in tiers[:4]],
        )
