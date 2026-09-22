from __future__ import annotations

import json
from importlib.resources import files


def load_builtin(name: str) -> dict:
    resource = files(__package__).joinpath(f"{name}.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def available() -> list[str]:
    return ["publication", "waveform", "minimal"]

