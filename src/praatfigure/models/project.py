from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .figure import FigureSpec


@dataclass(slots=True)
class Project:
    audio_path: str
    textgrid_path: str
    figure_spec: FigureSpec
    preset: str = "publication"
    export_destination: str | None = None
    recent_selections: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "audio_path": self.audio_path,
            "textgrid_path": self.textgrid_path,
            "figure_spec": self.figure_spec.to_dict(),
            "preset": self.preset,
            "export_destination": self.export_destination,
            "recent_selections": self.recent_selections,
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            audio_path=data["audio_path"],
            textgrid_path=data["textgrid_path"],
            figure_spec=FigureSpec.from_dict(data["figure_spec"]),
            preset=data.get("preset", "publication"),
            export_destination=data.get("export_destination"),
            recent_selections=data.get("recent_selections", []),
        )
