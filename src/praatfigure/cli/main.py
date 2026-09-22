from __future__ import annotations

import argparse
from pathlib import Path

from matplotlib import pyplot as plt

from ..io import load_audio, load_textgrid
from ..models.figure import FigureSpec
from ..models.project import Project
from ..models.selection import Target, TimeRange
from ..render import Renderer, export_figure
from ..render.renderer import sanitise_filename


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="praatfigure", description="Create phonetic figures from audio and TextGrid")
    sub = parser.add_subparsers(dest="command")
    render = sub.add_parser("render", help="Render one annotation")
    _source_arguments(render)
    group = render.add_mutually_exclusive_group(required=True)
    group.add_argument("--label", help="Exact annotation label")
    group.add_argument("--regex", help="Regular expression matched against annotations")
    render.add_argument("--occurrence", type=int, default=1, help="One-based matching occurrence")
    render.add_argument("--output", required=True)
    render.add_argument("--show-duration", action="store_true")
    render.add_argument("--overwrite", action="store_true")

    batch = sub.add_parser("batch", help="Render every matching annotation")
    _source_arguments(batch)
    group = batch.add_mutually_exclusive_group(required=True)
    group.add_argument("--label", help="Exact annotation label")
    group.add_argument("--regex", help="Regular expression matched against annotations")
    batch.add_argument("--output-dir", required=True)
    batch.add_argument("--format", choices=["svg", "pdf", "png"], default="png")

    project = sub.add_parser("render-project", help="Render a saved project")
    project.add_argument("project")
    project.add_argument("--output", required=True)
    project.add_argument("--overwrite", action="store_true")
    return parser


def _source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--audio", required=True)
    parser.add_argument("--textgrid", required=True)
    parser.add_argument("--tier", required=True)
    parser.add_argument("--padding-left", type=float, default=0.1)
    parser.add_argument("--padding-right", type=float, default=0.1)
    parser.add_argument("--time-mode", choices=["absolute", "relative_to_view_start", "relative_to_target_start"],
                        default="relative_to_view_start")


def _matches(args, grid):
    tier = grid.tier(args.tier)
    if tier.kind != "interval":
        raise ValueError("Rendering selections currently requires an IntervalTier")
    return tier.search(args.regex if args.regex is not None else args.label,
                       "regex" if args.regex is not None else "exact")


def _spec(args, grid, entry) -> FigureSpec:
    target = Target(entry.start, entry.end, args.tier, entry.index, entry.label)
    view = TimeRange(entry.start, entry.end).padded(
        args.padding_left, args.padding_right, minimum=grid.xmin, maximum=grid.xmax
    )
    tiers = [tier.name for tier in grid.tiers if tier.non_empty][:4]
    spec = FigureSpec.publication(view, [target], tiers)
    spec.time_mode = args.time_mode
    if hasattr(args, "show_duration"):
        spec.duration.visible = args.show_duration
    return spec


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.command:
        return launch_gui_or_help()
    renderer = Renderer()
    if args.command == "render-project":
        project = Project.load(args.project)
        audio = load_audio(project.audio_path)
        grid = load_textgrid(project.textgrid_path)
        figure = renderer.render(audio, grid, project.figure_spec)
        export_figure(figure, args.output, dpi=project.figure_spec.appearance.dpi, overwrite=args.overwrite)
        plt.close(figure)
        return 0
    audio = load_audio(args.audio)
    grid = load_textgrid(args.textgrid)
    matches = _matches(args, grid)
    if not matches:
        raise SystemExit("No matching annotations found")
    if args.command == "render":
        index = args.occurrence - 1
        if index < 0 or index >= len(matches):
            raise SystemExit(f"Occurrence {args.occurrence} does not exist ({len(matches)} matches)")
        spec = _spec(args, grid, matches[index])
        figure = renderer.render(audio, grid, spec)
        export_figure(figure, args.output, dpi=spec.appearance.dpi, overwrite=args.overwrite)
        plt.close(figure)
        return 0
    output_dir = Path(args.output_dir)
    for occurrence, entry in enumerate(matches, 1):
        spec = _spec(args, grid, entry)
        figure = renderer.render(audio, grid, spec)
        stem = sanitise_filename(f"{Path(args.audio).stem}_{args.tier}_{entry.label}_{entry.index}_{occurrence}")
        destination = output_dir / f"{stem}.{args.format}"
        if destination.exists():
            destination = output_dir / f"{stem}_{entry.start:.3f}.{args.format}"
        export_figure(figure, destination, dpi=spec.appearance.dpi)
        plt.close(figure)
    return 0


def launch_gui_or_help() -> int:
    try:
        from ..gui.main_window import launch
    except ImportError as exc:
        _parser().print_help()
        print(f"\nDesktop GUI unavailable: {exc}")
        return 2
    return launch()
