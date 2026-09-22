from __future__ import annotations

from pathlib import Path

from praatio import textgrid as praatio_textgrid

from ..models.textgrid import Annotation, TextGridDocument, Tier


def load_textgrid(path: str | Path) -> TextGridDocument:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    grid = praatio_textgrid.openTextgrid(
        str(source), includeEmptyIntervals=True, reportingMode="warning", duplicateNamesMode="error"
    )
    tiers: list[Tier] = []
    for tier_name in grid.tierNames:
        raw_tier = grid.getTier(tier_name)
        kind = "interval" if isinstance(raw_tier, praatio_textgrid.IntervalTier) else "point"
        entries: list[Annotation] = []
        for index, raw in enumerate(raw_tier.entries):
            if kind == "interval":
                entries.append(Annotation(index, float(raw.start), float(raw.end), str(raw.label)))
            else:
                entries.append(Annotation(index, float(raw.time), None, str(raw.label)))
        tiers.append(Tier(tier_name, kind, entries))
    return TextGridDocument(float(grid.minTimestamp), float(grid.maxTimestamp), tiers, str(source))


def validate_domains(audio_start: float, audio_end: float, grid: TextGridDocument,
                     tolerance: float = 0.02) -> list[str]:
    warnings: list[str] = []
    start_delta = abs(audio_start - grid.xmin)
    end_delta = abs(audio_end - grid.xmax)
    if max(start_delta, end_delta) > tolerance:
        warnings.append(
            f"Audio and TextGrid time domains differ (start {start_delta:.3f}s, end {end_delta:.3f}s)."
        )
    for tier in grid.tiers:
        previous_end: float | None = None
        for entry in tier.entries:
            if entry.end is not None:
                if entry.end <= entry.start:
                    warnings.append(f"{tier.name}[{entry.index}] has non-positive duration")
                if previous_end is not None and entry.start < previous_end - 1e-9:
                    warnings.append(f"{tier.name}[{entry.index}] overlaps the previous interval")
                previous_end = entry.end
    return warnings

