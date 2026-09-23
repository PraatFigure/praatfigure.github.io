from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


@dataclass(slots=True)
class Track:
    kind: str
    height: float = 1.0
    visible: bool = True
    display_name: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class WaveformTrack(Track):
    kind: str = "waveform"
    height: float = 1.0
    channel: Literal["left", "right", "average", "separate"] = "separate"
    symmetric: bool = True
    zero_line: bool = True
    line_width: float = 0.7
    show_y_ticks: bool = False
    show_y_label: bool = False


@dataclass(slots=True)
class SpectrogramTrack(Track):
    kind: str = "spectrogram"
    height: float = 1.0
    maximum_frequency: float = 5000.0
    window_length: float = 0.005
    dynamic_range: float = 70.0
    preemphasis_from: float = 50.0
    dynamic_compression: float = 0.25
    cmap: str = "Greys"
    pitch: bool = False
    formants: list[int] = field(default_factory=list)
    pitch_floor: float = 75.0
    pitch_ceiling: float = 600.0
    formant_ceiling: float = 5500.0
    time_step: float = 0.001
    frequency_step: float = 10.0
    show_frequency_ticks: bool = True
    show_y_label: bool = False


@dataclass(slots=True)
class PitchTrack(Track):
    kind: str = "pitch"
    height: float = 1.0
    floor: float = 75.0
    ceiling: float = 600.0


@dataclass(slots=True)
class AnnotationTrack(Track):
    kind: str = "annotation"
    height: float = 0.5
    tier: str = ""
    show_empty: bool = False
    show_tier_name: Literal["left", "right", "hidden"] = "hidden"


TRACK_TYPES = {
    "waveform": WaveformTrack,
    "spectrogram": SpectrogramTrack,
    "pitch": PitchTrack,
    "annotation": AnnotationTrack,
}


def track_from_dict(data: dict) -> Track:
    payload = dict(data)
    kind = payload.get("kind")
    try:
        return TRACK_TYPES[kind](**payload)
    except KeyError as exc:
        raise ValueError(f"Unsupported track kind: {kind}") from exc
