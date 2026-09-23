from __future__ import annotations

import os
import re
import textwrap
from pathlib import Path

import matplotlib
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle
from matplotlib.textpath import TextPath
import numpy as np

from ..analysis import AnalysisCache
from ..analysis import formants as calculate_formants
from ..analysis import pitch as calculate_pitch
from ..analysis import spectrogram as calculate_spectrogram
from ..io.audio import AudioData
from ..models.figure import FigureSpec
from ..models.selection import TimeTransform
from ..models.textgrid import TextGridDocument, Tier
from ..models.tracks import AnnotationTrack, PitchTrack, SpectrogramTrack, WaveformTrack


def sanitise_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return value or "figure"


class Renderer:
    def __init__(self, cache: AnalysisCache | None = None) -> None:
        self.cache = cache or AnalysisCache()

    def render(self, audio: AudioData, grid: TextGridDocument, spec: FigureSpec):
        spec.validate()
        visible = [track for track in spec.tracks if track.visible]
        height_units = sum(max(0.1, track.height) for track in visible)
        width_inches = spec.appearance.width_mm / 25.4
        height_inches = max(2.4, 1.15 * height_units + 0.45)
        transform = TimeTransform(
            spec.time_mode, spec.view_range.start,
            spec.targets[0].start if spec.targets else None,
        )
        with matplotlib.rc_context({
            "font.family": spec.appearance.font_family,
            "font.size": spec.appearance.base_font_size,
            "axes.edgecolor": spec.appearance.foreground,
            "text.color": spec.appearance.foreground,
            "xtick.color": spec.appearance.foreground,
            "ytick.color": spec.appearance.foreground,
            "figure.facecolor": spec.appearance.background,
        }):
            figure = Figure(figsize=(width_inches, height_inches),
                            facecolor=spec.appearance.background)
            axes = figure.subplots(
                len(visible), 1, sharex=True, squeeze=False,
                gridspec_kw={"height_ratios": [max(0.1, t.height) for t in visible],
                             "hspace": spec.appearance.panel_spacing},
            )
            axes_list = list(axes[:, 0])
            x0 = float(transform.forward(spec.view_range.start))
            x1 = float(transform.forward(spec.view_range.end))
            for axis, track in zip(axes_list, visible):
                axis.set_xlim(x0, x1)
                axis.set_facecolor(spec.appearance.background)
                if isinstance(track, WaveformTrack):
                    self._draw_waveform(axis, audio, spec, transform, track)
                elif isinstance(track, SpectrogramTrack):
                    self._draw_spectrogram(axis, audio, spec, transform, track)
                elif isinstance(track, PitchTrack):
                    self._draw_pitch(axis, audio, spec, transform, track)
                elif isinstance(track, AnnotationTrack):
                    self._draw_annotation(axis, grid.tier(track.tier), spec, transform, track)
            self._draw_boundaries(axes_list, visible, grid, spec, transform)
            self._draw_target_time_labels(axes_list, visible, spec, transform)
            self._draw_duration(axes_list[0], spec, transform)
            for axis in axes_list[:-1]:
                axis.tick_params(axis="x", labelbottom=False)
            for axis in axes_list:
                axis.margins(x=0)
                axis.tick_params(axis="both", labelsize=spec.appearance.axis_font_size)
                for spine in axis.spines.values():
                    spine.set_linewidth(0.8)
            if spec.show_x_axis:
                if spec.x_ticks_mode == "endpoints":
                    axes_list[-1].set_xticks([x0, x1])
                elif spec.x_ticks_mode == "hidden":
                    axes_list[-1].tick_params(axis="x", labelbottom=False)
                if spec.show_time_label:
                    axes_list[-1].set_xlabel("Time [s]")
            else:
                axes_list[-1].tick_params(axis="x", labelbottom=False)
            figure.align_ylabels(axes_list)
            left, right = self._horizontal_margins(spec, visible, x0, x1, width_inches)
            bottom = 0.1 if spec.show_time_label else 0.075
            has_top_text = spec.boundary_projection.label_target_times or spec.duration.visible
            top = 0.89 if (spec.boundary_projection.label_target_times and spec.duration.visible) else (
                0.93 if has_top_text else 0.98
            )
            figure.subplots_adjust(left=left, right=right, top=top, bottom=bottom,
                                   hspace=spec.appearance.panel_spacing)
            return figure

    def _horizontal_margins(self, spec, tracks, x0: float, x1: float,
                            width_inches: float) -> tuple[float, float]:
        """Reserve enough space for endpoint ticks and optional tier names."""
        def text_width(value: str, size: float) -> float:
            try:
                path = TextPath(
                    (0, 0), value,
                    prop=FontProperties(family=spec.appearance.font_family, size=size),
                )
                return max(0.0, path.get_extents().width / 72)
            except Exception:
                return len(value) * size * 0.58 / 72

        axis_size = spec.appearance.axis_font_size
        endpoint_half = max(
            text_width(f"{x0:.4f}", axis_size), text_width(f"{x1:.4f}", axis_size)
        ) / 2 + 0.06
        left_inches = max(0.18, endpoint_half)
        right_inches = max(0.12, endpoint_half)
        if any(isinstance(track, SpectrogramTrack) and track.show_frequency_ticks for track in tracks):
            left_inches = max(left_inches, 0.43)
        for track in tracks:
            if not isinstance(track, AnnotationTrack) or track.show_tier_name == "hidden":
                continue
            name = track.display_name or track.tier
            wrapped = self._wrapped_tier_name(name)
            name_width = max(
                (text_width(line, spec.appearance.base_font_size) for line in wrapped.splitlines()),
                default=0.0,
            ) + 0.2
            if track.show_tier_name == "left":
                left_inches = max(left_inches, name_width)
            else:
                right_inches = max(right_inches, name_width)
        left = min(0.62, left_inches / width_inches)
        right = 1.0 - min(0.62, right_inches / width_inches)
        if right - left < 0.25:
            midpoint = (left + right) / 2
            left, right = midpoint - 0.125, midpoint + 0.125
        return left, right

    def _audio_key(self, audio: AudioData) -> tuple:
        mtime = os.path.getmtime(audio.path) if audio.path and os.path.exists(audio.path) else None
        return audio.path or id(audio), mtime

    def _draw_waveform(self, axis, audio, spec, transform, track: WaveformTrack) -> None:
        times, values = audio.window(spec.view_range.start, spec.view_range.end, track.channel)
        if values.ndim == 2 and track.channel == "separate":
            count = values.shape[1]
            peak = max(0.01, float(np.nanmax(np.abs(values))))
            normalised = values / peak * 0.42
            offsets = np.arange(count - 1, -1, -1, dtype=float)
            for channel_index, offset in enumerate(offsets):
                axis.plot(transform.forward(times), normalised[:, channel_index] + offset,
                          color="#111111", lw=track.line_width, rasterized=False)
                if track.zero_line:
                    axis.axhline(offset, color="#777777", lw=0.3, zorder=0)
            axis.set_ylim(-0.55, max(0.55, count - 0.45))
        else:
            axis.plot(transform.forward(times), values, color="#111111", lw=track.line_width, rasterized=False)
            if track.zero_line:
                axis.axhline(0, color="#777777", lw=0.4, zorder=0)
            if track.symmetric and values.size:
                peak = max(0.01, float(np.nanmax(np.abs(values))))
                axis.set_ylim(-peak * 1.05, peak * 1.05)
        if not track.show_y_ticks:
            axis.set_yticks([])
        if track.show_y_label:
            axis.set_ylabel(track.display_name or "Amplitude")
        axis.margins(x=0)

    def _draw_spectrogram(self, axis, audio, spec, transform, track: SpectrogramTrack) -> None:
        key = self._audio_key(audio) + ("spectrogram", spec.view_range.start, spec.view_range.end,
              track.window_length, track.maximum_frequency, track.dynamic_range,
              track.time_step, track.frequency_step, track.preemphasis_from,
              track.dynamic_compression)
        frequencies, times, power = self.cache.get_or_create(key, lambda: calculate_spectrogram(
            audio, spec.view_range.start, spec.view_range.end,
            window_length=track.window_length,
            maximum_frequency=track.maximum_frequency,
            dynamic_range=track.dynamic_range,
            time_step=track.time_step,
            frequency_step=track.frequency_step,
            preemphasis_from=track.preemphasis_from,
            dynamic_compression=track.dynamic_compression,
        ))
        display_times = np.asarray(transform.forward(times), dtype=float)
        x0, x1 = axis.get_xlim()
        x_edges = self._cell_edges(display_times, x0, x1)
        y_edges = self._cell_edges(np.asarray(frequencies, dtype=float), 0.0,
                                   track.maximum_frequency)
        axis.imshow(
            power, origin="lower", aspect="auto", cmap=track.cmap,
            extent=(x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]),
            interpolation=track.interpolation, interpolation_stage="rgba",
            rasterized=True,
        )
        axis.set_ylim(0, track.maximum_frequency)
        if track.show_frequency_ticks:
            step = 1000 if track.maximum_frequency >= 4000 else 500
            axis.set_yticks(np.arange(0, track.maximum_frequency + 0.1, step))
        else:
            axis.set_yticks([])
        if track.show_y_label:
            axis.set_ylabel(track.display_name or "Frequency [Hz]")
        if track.pitch:
            self._pitch_overlay(axis, audio, spec, transform, track.pitch_floor, track.pitch_ceiling)
        if track.formants:
            key = self._audio_key(audio) + ("formants", spec.view_range.start, spec.view_range.end,
                                             tuple(track.formants), track.formant_ceiling)
            values = self.cache.get_or_create(key, lambda: calculate_formants(
                audio, spec.view_range.start, spec.view_range.end,
                track.formants, track.formant_ceiling,
            ))
            for index, (times_f, frequencies_f) in values.items():
                axis.scatter(transform.forward(times_f), frequencies_f, s=5, marker=".",
                             label=f"F{index}", zorder=5)

    @staticmethod
    def _cell_edges(centres: np.ndarray, lower: float, upper: float) -> np.ndarray:
        """Convert regularly sampled cell centres into gap-free image edges."""
        if centres.size == 0:
            return np.array([lower, upper], dtype=float)
        if centres.size == 1:
            return np.array([lower, upper], dtype=float)
        midpoints = (centres[:-1] + centres[1:]) / 2
        edges = np.concatenate((
            [centres[0] - (centres[1] - centres[0]) / 2],
            midpoints,
            [centres[-1] + (centres[-1] - centres[-2]) / 2],
        ))
        # Ensure the image reaches the frame when the requested view begins or
        # ends between valid analysis centres (notably at the audio boundary).
        if centres[0] >= lower:
            edges[0] = lower
        if centres[-1] <= upper:
            edges[-1] = upper
        return edges

    def _pitch_overlay(self, axis, audio, spec, transform, floor: float, ceiling: float) -> None:
        key = self._audio_key(audio) + ("pitch", spec.view_range.start, spec.view_range.end, floor, ceiling)
        times, values = self.cache.get_or_create(key, lambda: calculate_pitch(
            audio, spec.view_range.start, spec.view_range.end, floor, ceiling
        ))
        twin = axis.twinx()
        twin.plot(transform.forward(times), values, color="#2020aa", marker=".", ms=2.5, lw=0.7)
        twin.set_ylim(floor, ceiling)
        twin.set_ylabel("F0 [Hz]", color="#2020aa")
        twin.set_xlim(axis.get_xlim())

    def _draw_pitch(self, axis, audio, spec, transform, track: PitchTrack) -> None:
        self._pitch_overlay(axis, audio, spec, transform, track.floor, track.ceiling)
        axis.set_yticks([])

    def _draw_annotation(self, axis, tier: Tier, spec, transform, track: AnnotationTrack) -> None:
        axis.set_ylim(0, 1)
        axis.set_yticks([])
        axis.spines["left"].set_visible(True)
        axis.spines["right"].set_visible(True)
        if tier.kind == "interval":
            for entry in tier.entries:
                if entry.end is None or entry.end < spec.view_range.start or entry.start > spec.view_range.end:
                    continue
                left = max(entry.start, spec.view_range.start)
                right = min(entry.end, spec.view_range.end)
                x = float(transform.forward(left))
                width = right - left
                axis.add_patch(Rectangle((x, 0), width, 1, fill=False, edgecolor="#222222", lw=0.65))
                if entry.label and (track.show_empty or entry.label.strip()):
                    axis_width_inches = max(1.0, spec.appearance.width_mm / 25.4 * 0.885)
                    text_width_inches = len(entry.label) * spec.appearance.annotation_font_size * 0.58 / 72
                    approx_required = text_width_inches / axis_width_inches * spec.view_range.duration
                    if width >= approx_required:
                        axis.text(x + width / 2, 0.5, entry.label, ha="center", va="center",
                                  fontsize=spec.appearance.annotation_font_size, clip_on=True)
        else:
            for entry in tier.entries:
                if spec.view_range.start <= entry.start <= spec.view_range.end:
                    x = float(transform.forward(entry.start))
                    axis.axvline(x, color="#222222", lw=0.7)
                    axis.plot([x], [0.52], "o", color="#222222", ms=2.5)
                    axis.text(x, 0.64, entry.label, ha="center", va="bottom",
                              fontsize=spec.appearance.annotation_font_size, clip_on=True)
        if track.show_tier_name != "hidden":
            x = -0.015 if track.show_tier_name == "left" else 1.015
            name = track.display_name or tier.display_name or tier.name
            axis.text(x, 0.5, self._wrapped_tier_name(name),
                      transform=axis.transAxes, ha="right" if x < 0 else "left", va="center")

    @staticmethod
    def _wrapped_tier_name(name: str) -> str:
        return "\n".join(textwrap.wrap(name, width=28, break_long_words=True,
                                       break_on_hyphens=True)) or name

    def _boundary_times(self, tracks, grid, spec) -> list[float]:
        mode = spec.boundary_projection.mode
        if mode == "none":
            return []
        if mode == "target_only":
            return [value for target in spec.targets for value in (target.start, target.end)]
        if mode == "selected_tiers":
            names = set(spec.boundary_projection.tiers)
        elif mode == "all_tiers":
            names = {tier.name for tier in grid.tiers}
        else:
            names = {track.tier for track in tracks if isinstance(track, AnnotationTrack)}
        times: list[float] = []
        for name in names:
            tier = grid.tier(name)
            for entry in tier.entries:
                times.append(entry.start)
                if entry.end is not None:
                    times.append(entry.end)
        times = sorted(t for t in times if spec.view_range.start <= t <= spec.view_range.end)
        if spec.boundary_projection.merge:
            merged: list[float] = []
            for value in times:
                if not merged or value - merged[-1] > spec.boundary_projection.tolerance:
                    merged.append(value)
            return merged
        return times

    def _draw_boundaries(self, axes, tracks, grid, spec, transform) -> None:
        times = self._boundary_times(tracks, grid, spec)
        for axis, track in zip(axes, tracks):
            if isinstance(track, AnnotationTrack):
                continue
            for value in times:
                axis.axvline(transform.forward(value), color="#333333",
                             lw=spec.boundary_projection.line_width,
                             ls=spec.boundary_projection.line_style,
                             alpha=spec.boundary_projection.opacity, zorder=6)

    def _draw_target_time_labels(self, axes, tracks, spec, transform) -> None:
        if not spec.boundary_projection.label_target_times or not spec.targets:
            return
        acoustic_axes = [
            axis for axis, track in zip(axes, tracks)
            if isinstance(track, (WaveformTrack, SpectrogramTrack, PitchTrack))
        ]
        if not acoustic_axes:
            return
        axis = acoustic_axes[0]
        values = sorted({value for target in spec.targets for value in (target.start, target.end)})
        displayed_values = [float(transform.forward(value)) for value in values]
        x0, x1 = axis.get_xlim()
        axis_width_inches = max(1.0, axis.figure.get_size_inches()[0] * 0.885)
        sample_label = f"{max(map(abs, displayed_values), default=0):.{spec.boundary_projection.target_time_decimals}f}"
        label_fraction = (
            len(sample_label) * spec.appearance.axis_font_size * 0.62 / 72 / axis_width_inches
        )
        clusters: list[list[float]] = []
        for displayed in displayed_values:
            if (not clusters or
                    (displayed - clusters[-1][-1]) / max(np.finfo(float).eps, x1 - x0) > label_fraction):
                clusters.append([displayed])
            else:
                clusters[-1].append(displayed)
        for cluster in clusters:
            for index, displayed in enumerate(cluster):
                if len(cluster) == 2:
                    horizontal = "right" if index == 0 else "left"
                    offset_x = -3 if index == 0 else 3
                    offset_y = 4
                elif len(cluster) > 2:
                    horizontal = "center"
                    offset_x = 0
                    offset_y = 4 + (index % 3) * spec.appearance.axis_font_size * 1.15
                else:
                    horizontal = "center"
                    offset_x = 0
                    offset_y = 4
                label = f"{displayed:.{spec.boundary_projection.target_time_decimals}f}"
                axis.annotate(
                    label, (displayed, 1.0), xycoords=("data", "axes fraction"),
                    xytext=(offset_x, offset_y), textcoords="offset points",
                    ha=horizontal, va="bottom", fontsize=spec.appearance.axis_font_size,
                    clip_on=False,
                    bbox={"facecolor": spec.appearance.background, "edgecolor": "none",
                          "alpha": 0.82, "pad": 0.25},
                )

    def _draw_duration(self, axis, spec, transform) -> None:
        if not spec.duration.visible:
            return
        for target in spec.targets:
            unit = spec.duration.unit
            if unit == "auto":
                unit = "ms" if target.duration < 1 else "s"
            value = target.duration * 1000 if unit == "ms" else target.duration
            text = f"{value:.{spec.duration.decimals}f} {unit}"
            x = (transform.forward(target.start) + transform.forward(target.end)) / 2
            offset = 5 + (spec.appearance.axis_font_size * 1.5
                          if spec.boundary_projection.label_target_times else 0)
            axis.annotate(text, (x, 1), xycoords=("data", "axes fraction"),
                          xytext=(0, offset), textcoords="offset points", ha="center", va="bottom",
                          fontsize=spec.appearance.axis_font_size,
                          bbox={"facecolor": spec.appearance.background, "edgecolor": "none",
                                "alpha": 0.82, "pad": 0.25})


def export_figure(figure, path: str | Path, *, dpi: int = 300, transparent: bool = False,
                  overwrite: bool = False) -> Path:
    destination = Path(path)
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")
    if destination.suffix.lower() not in {".svg", ".pdf", ".png"}:
        raise ValueError("Export format must be SVG, PDF, or PNG")
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=dpi, transparent=transparent,
                   facecolor="none" if transparent else figure.get_facecolor())
    return destination
