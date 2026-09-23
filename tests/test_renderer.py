import numpy as np
from matplotlib import pyplot as plt

from praatfigure.io.audio import AudioData
from praatfigure.io.textgrid import load_textgrid
from praatfigure.models.figure import FigureSpec
from praatfigure.models.selection import Target, TimeRange
from praatfigure.models.tracks import AnnotationTrack, SpectrogramTrack, WaveformTrack
from praatfigure.render import Renderer, export_figure, figure_to_png_bytes

from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "sample.TextGrid"


def test_default_track_heights():
    assert WaveformTrack().height == 1.0
    assert SpectrogramTrack().height == 1.0
    assert AnnotationTrack(tier="phones").height == 0.5


def test_spectrogram_raster_reaches_all_four_axis_boundaries():
    figure, _ = _render()
    axis = figure.axes[1]
    image = axis.images[0]
    left, right, bottom, top = image.get_extent()
    xlim = axis.get_xlim()
    ylim = axis.get_ylim()
    assert left <= xlim[0] and right >= xlim[1]
    assert bottom <= ylim[0] and top >= ylim[1]
    assert image.get_interpolation() == "bicubic"
    plt.close(figure)


def _render():
    sample_rate = 16000
    times = np.arange(sample_rate) / sample_rate
    audio = AudioData(np.sin(2 * np.pi * 220 * times), sample_rate, start_time=1.0)
    grid = load_textgrid(FIXTURE)
    spec = FigureSpec.publication(TimeRange(1.1, 1.7), [Target(1.25, 1.5, "phones", 1, "ə")], ["phones"])
    return Renderer().render(audio, grid, spec), spec


def test_renderer_has_shared_xlim_and_track_order():
    figure, spec = _render()
    assert len(figure.axes) == 3
    for axis in figure.axes:
        np.testing.assert_allclose(axis.get_xlim(), [0.0, 0.6])
    np.testing.assert_allclose(figure.axes[-1].get_xticks(), [0.0, 0.6])
    assert [track.height for track in spec.tracks] == [1.0, 1.0, 0.5]
    plt.close(figure)


def test_critical_boundary_alignment():
    figure, _ = _render()
    # Target boundary 1.25 is displayed at 0.15 on every track.
    for axis in figure.axes[:2]:
        positions = [float(line.get_xdata()[0]) for line in axis.lines if len(line.get_xdata()) == 2 and line.get_xdata()[0] == line.get_xdata()[1]]
        assert any(abs(value - 0.15) < 1e-12 for value in positions)
        display_positions = [axis.transData.transform((value, 0))[0] for value in positions if abs(value - 0.15) < 1e-12]
        assert display_positions
    annotation_edges = [patch.get_x() for patch in figure.axes[2].patches]
    assert any(abs(value - 0.15) < 1e-12 for value in annotation_edges)
    xs = [axis.transData.transform((0.15, 0))[0] for axis in figure.axes]
    np.testing.assert_allclose(xs, xs[0], atol=1e-9)
    plt.close(figure)


def test_exports_and_no_overwrite(tmp_path):
    figure, _ = _render()
    for suffix in ("svg", "pdf", "png"):
        destination = tmp_path / f"fə.{suffix}"
        export_figure(figure, destination, transparent=suffix == "png")
        assert destination.exists() and destination.stat().st_size > 0
        try:
            export_figure(figure, destination)
        except FileExistsError:
            pass
        else:
            raise AssertionError("Existing export was silently overwritten")
    plt.close(figure)


def test_figure_to_png_bytes():
    figure, _ = _render()
    try:
        png = figure_to_png_bytes(figure, dpi=300)
        assert png.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(png) > 1000
    finally:
        plt.close(figure)


def test_target_time_labels_and_annotation_outer_frame():
    figure, spec = _render()
    plt.close(figure)
    spec.boundary_projection.label_target_times = True
    sample_rate = 16000
    times = np.arange(sample_rate) / sample_rate
    audio = AudioData(np.sin(2 * np.pi * 220 * times), sample_rate, start_time=1.0)
    figure = Renderer().render(audio, load_textgrid(FIXTURE), spec)
    labels = {text.get_text() for text in figure.axes[0].texts}
    assert {"0.150", "0.400"}.issubset(labels)
    annotation_axis = figure.axes[-1]
    assert annotation_axis.spines["left"].get_visible()
    assert annotation_axis.spines["right"].get_visible()
    plt.close(figure)


def test_short_target_time_labels_are_pushed_apart():
    sample_rate = 16000
    times = np.arange(sample_rate) / sample_rate
    audio = AudioData(np.sin(2 * np.pi * 220 * times), sample_rate, start_time=1.0)
    grid = load_textgrid(FIXTURE)
    spec = FigureSpec.publication(
        TimeRange(1.1, 1.7), [Target(1.25, 1.251, "phones", 1, "ə")], ["phones"]
    )
    spec.boundary_projection.label_target_times = True
    assert spec.boundary_projection.line_width == 1.1
    figure = Renderer().render(audio, grid, spec)
    labels = figure.axes[0].texts
    assert [label.get_ha() for label in labels] == ["right", "left"]
    plt.close(figure)


def test_long_tier_name_expands_margin_and_duration_is_independent():
    sample_rate = 16000
    times = np.arange(sample_rate) / sample_rate
    audio = AudioData(np.sin(2 * np.pi * 220 * times), sample_rate, start_time=1.0)
    grid = load_textgrid(FIXTURE)
    spec = FigureSpec.publication(
        TimeRange(1.1, 1.7), [Target(1.25, 1.5, "phones", 1, "ə")], ["phones"]
    )
    assert spec.appearance.axis_font_size == 6.0
    annotation = spec.tracks[-1]
    annotation.show_tier_name = "left"
    annotation.display_name = "Very long publication tier name"
    spec.boundary_projection.mode = "none"
    spec.boundary_projection.label_target_times = False
    spec.duration.visible = True
    figure = Renderer().render(audio, grid, spec)
    assert figure.subplotpars.left > 0.2
    assert any(text.get_text().endswith("ms") for text in figure.axes[0].texts)
    verticals = [
        line for line in figure.axes[0].lines
        if len(line.get_xdata()) == 2 and line.get_xdata()[0] == line.get_xdata()[1]
    ]
    assert not verticals
    plt.close(figure)
