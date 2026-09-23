from __future__ import annotations

from copy import deepcopy
import json
import sys
import unicodedata
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QSplitter, QTableWidget,
    QScrollArea, QTableWidgetItem, QToolBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib import pyplot as plt

from ..io import load_audio, load_textgrid
from ..models.figure import FigureSpec
from ..models.project import Project
from ..models.selection import Target, TimeRange
from ..models.tracks import AnnotationTrack, SpectrogramTrack, WaveformTrack
from ..render import Renderer, export_figure
from ..render.renderer import sanitise_filename


class _RenderSignals(QObject):
    ready = Signal(int, object)
    failed = Signal(int, str)
    finished = Signal(int)


class _RenderJob(QRunnable):
    def __init__(self, generation, renderer, audio, grid, spec) -> None:
        super().__init__()
        self.generation = generation
        self.renderer = renderer
        self.audio = audio
        self.grid = grid
        self.spec = spec
        self.signals = _RenderSignals()

    def run(self) -> None:
        try:
            figure = self.renderer.render(self.audio, self.grid, self.spec)
            self.signals.ready.emit(self.generation, figure)
        except Exception as exc:
            self.signals.failed.emit(self.generation, str(exc))
        finally:
            self.signals.finished.emit(self.generation)


class TrackTreeWidget(QTreeWidget):
    orderChanged = Signal()

    def dropEvent(self, event) -> None:
        super().dropEvent(event)
        self.orderChanged.emit()


class ExportDialog(QDialog):
    def __init__(self, parent, directory: str, filename: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export figure")
        layout = QGridLayout(self)
        self.directory = QLineEdit(directory)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        self.filename = QLineEdit(filename)
        self.format = QComboBox()
        self.format.addItems(["PNG", "SVG", "PDF"])
        self.dpi = QDoubleSpinBox()
        self.dpi.setRange(72, 1200)
        self.dpi.setDecimals(0)
        self.dpi.setValue(300)
        self.transparent = QCheckBox("Transparent background (PNG)")
        layout.addWidget(QLabel("Folder"), 0, 0)
        layout.addWidget(self.directory, 0, 1)
        layout.addWidget(browse, 0, 2)
        layout.addWidget(QLabel("Filename"), 1, 0)
        layout.addWidget(self.filename, 1, 1, 1, 2)
        layout.addWidget(QLabel("Format"), 2, 0)
        layout.addWidget(self.format, 2, 1, 1, 2)
        layout.addWidget(QLabel("DPI"), 3, 0)
        layout.addWidget(self.dpi, 3, 1, 1, 2)
        layout.addWidget(self.transparent, 4, 1, 1, 2)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, 5, 0, 1, 3)

    def _browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Export folder", self.directory.text())
        if directory:
            self.directory.setText(directory)

    def destination(self) -> Path:
        stem = sanitise_filename(unicodedata.normalize("NFC", self.filename.text()))
        return Path(self.directory.text()) / f"{stem}.{self.format.currentText().lower()}"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PraatFigure")
        self.resize(1240, 780)
        self.audio = None
        self.grid = None
        self.audio_path: str | None = None
        self.grid_path: str | None = None
        self._source_label: str | None = None
        self._last_export_directory: str | None = None
        self.spec: FigureSpec | None = None
        self.renderer = Renderer()
        self.current_figure = None
        self._entries = []
        self._source_range: TimeRange | None = None
        self._updating_target_checks = False
        self._render_generation = 0
        self._render_busy = False
        self._rerender_pending = False
        self._render_jobs: set[_RenderJob] = set()
        self._render_pool = QThreadPool(self)
        self._render_pool.setMaxThreadCount(1)
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self.refresh_preview)

    def _build_ui(self) -> None:
        toolbar = QToolBar("Quick controls")
        toolbar.setObjectName("quick-controls")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setContextMenuPolicy(Qt.PreventContextMenu)
        self.addToolBar(toolbar)
        self.pitch_toggle = QCheckBox("Pitch")
        self.formant_toggle = QCheckBox("Formants")
        self.bounds_toggle = QCheckBox("Boundary lines")
        self.bounds_toggle.setChecked(True)
        self.duration_toggle = QCheckBox("Duration")
        quick_help = {
            self.pitch_toggle: "Overlay the pitch contour on the spectrogram",
            self.formant_toggle: "Overlay F1 and F2 on the spectrogram",
            self.bounds_toggle: "Project the selected target boundaries through acoustic tracks",
            self.duration_toggle: "Show the duration of selected target segments",
        }
        for widget in (self.pitch_toggle, self.formant_toggle,
                       self.bounds_toggle, self.duration_toggle):
            widget.setToolTip(quick_help[widget])
            toolbar.addWidget(widget)
            widget.toggled.connect(self.schedule_preview)
        export_button = QPushButton("Export…")
        export_button.clicked.connect(self.export)
        open_project_button = QPushButton("Open project…")
        open_project_button.clicked.connect(self.open_project)
        save_project_button = QPushButton("Save project…")
        save_project_button.clicked.connect(self.save_project)
        toolbar.addWidget(open_project_button)
        toolbar.addWidget(save_project_button)
        toolbar.addWidget(export_button)
        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction(toolbar.toggleViewAction())
        template_menu = self.menuBar().addMenu("Templates")
        template_menu.addAction("Save settings template…", self.save_template)
        template_menu.addAction("Load settings template…", self.load_template)
        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction("Quick start and controls", self.show_help)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._left_panel())
        preview = QWidget()
        preview_layout = QVBoxLayout(preview)
        self.status_label = QLabel("Open an audio file and its TextGrid to begin.")
        self.canvas = FigureCanvasQTAgg(plt.figure(figsize=(8, 5)))
        self.canvas.setMinimumSize(100, 100)
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(False)
        self.preview_scroll.setAlignment(Qt.AlignCenter)
        self.preview_scroll.setWidget(self.canvas)
        preview_layout.addWidget(self.preview_scroll, 1)
        preview_layout.addWidget(self.status_label)
        splitter.addWidget(preview)
        splitter.setSizes([320, 1280])
        self.setCentralWidget(splitter)

    def _left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        audio_button = QPushButton("Open audio…")
        grid_button = QPushButton("Open TextGrid…")
        audio_button.clicked.connect(self.open_audio)
        grid_button.clicked.connect(self.open_textgrid)
        self.audio_label = QLabel("Audio: —")
        self.grid_label = QLabel("TextGrid: —")
        layout.addWidget(audio_button)
        layout.addWidget(self.audio_label)
        layout.addWidget(grid_button)
        layout.addWidget(self.grid_label)

        layout.addWidget(QLabel("Find segment"))
        self.tier_combo = QComboBox()
        self.tier_combo.currentTextChanged.connect(self.populate_table)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search annotation")
        self.search.textChanged.connect(self.populate_table)
        self.search_mode = QComboBox()
        self.search_mode.addItems(["contains", "exact", "regex"])
        self.search_mode.currentTextChanged.connect(self.populate_table)
        row = QHBoxLayout()
        row.addWidget(self.search, 1)
        row.addWidget(self.search_mode)
        layout.addWidget(self.tier_combo)
        layout.addLayout(row)
        self.table = QTableWidget(0, 5)
        self.table.setMinimumHeight(190)
        self.table.setHorizontalHeaderLabels(["#", "Label", "Start", "End", "ms"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.doubleClicked.connect(self.select_row)
        layout.addWidget(self.table, 2)
        use_interval = QPushButton("Render selected interval")
        use_interval.clicked.connect(self.select_current_row)
        layout.addWidget(use_interval)

        form = QFormLayout()
        self.left_padding = QDoubleSpinBox()
        self.right_padding = QDoubleSpinBox()
        for spin in (self.left_padding, self.right_padding):
            spin.setRange(0, 30)
            spin.setDecimals(3)
            spin.setSingleStep(0.05)
            spin.setValue(0.0)
        self.time_mode = QComboBox()
        self.time_mode.addItem("Reset to zero", "relative_to_view_start")
        self.time_mode.addItem("Original time", "absolute")
        self.time_mode.addItem("Zero at target", "relative_to_target_start")
        self.time_mode.currentIndexChanged.connect(self.schedule_preview)
        form.addRow("Left context [s]", self.left_padding)
        form.addRow("Right context [s]", self.right_padding)
        form.addRow("Time mode", self.time_mode)
        self.manual_start = QDoubleSpinBox()
        self.manual_end = QDoubleSpinBox()
        for spin in (self.manual_start, self.manual_end):
            spin.setRange(-86400, 86400)
            spin.setDecimals(4)
        manual_button = QPushButton("Use manual timespan")
        manual_button.clicked.connect(self.use_manual_timespan)
        form.addRow("Start [s]", self.manual_start)
        form.addRow("End [s]", self.manual_end)
        form.addRow("", manual_button)
        layout.addLayout(form)

        layout.addWidget(QLabel("Target boundaries inside the view"))
        self.target_tier_combo = QComboBox()
        self.target_tier_combo.currentTextChanged.connect(self._populate_target_entries)
        self.target_entries = QListWidget()
        self.target_entries.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.target_entries.setMinimumHeight(150)
        self.target_entries.itemChanged.connect(self._target_checks_changed)
        use_targets = QPushButton("Project selected boundaries")
        use_targets.clicked.connect(self.use_selected_targets)
        clear_targets = QPushButton("Clear projected boundaries")
        clear_targets.clicked.connect(self.clear_selected_targets)
        layout.addWidget(self.target_tier_combo)
        layout.addWidget(self.target_entries)
        layout.addWidget(use_targets)
        layout.addWidget(clear_targets)

        layout.addWidget(QLabel("Tracks (edit name/height; drag to reorder)"))
        self.tracks = TrackTreeWidget()
        self.tracks.setColumnCount(3)
        self.tracks.setHeaderLabels(["Show", "Name on figure", "Height"])
        self.tracks.setRootIsDecorated(False)
        self.tracks.setAlternatingRowColors(True)
        self.tracks.setMinimumHeight(190)
        self.tracks.setDragDropMode(QAbstractItemView.InternalMove)
        self.tracks.orderChanged.connect(self.schedule_preview_immediate)
        self.tracks.itemChanged.connect(self.schedule_preview)
        self.tracks.currentItemChanged.connect(self._track_selected)
        self.tracks.header().resizeSection(0, 55)
        self.tracks.header().resizeSection(1, 185)
        self.tracks.header().resizeSection(2, 75)
        layout.addWidget(self.tracks, 1)
        height_row = QHBoxLayout()
        height_row.addWidget(QLabel("Selected track height"))
        self.track_height = QDoubleSpinBox()
        self.track_height.setRange(0.2, 5.0)
        self.track_height.setDecimals(2)
        self.track_height.setSingleStep(0.1)
        self.track_height.setValue(1.0)
        self.track_height.valueChanged.connect(self._set_selected_track_height)
        height_row.addWidget(self.track_height)
        layout.addLayout(height_row)

        display_row = QFormLayout()
        self.time_ticks = QComboBox()
        self.time_ticks.addItem("Start and end", "endpoints")
        self.time_ticks.addItem("Automatic", "automatic")
        self.time_ticks.addItem("Hidden", "hidden")
        self.time_label_toggle = QCheckBox("Show Time [s] label")
        self.wave_axis_toggle = QCheckBox("Show waveform y-axis")
        self.frequency_ticks_toggle = QCheckBox("Show spectrogram Hz ticks")
        self.frequency_ticks_toggle.setChecked(True)
        self.tier_names_toggle = QCheckBox("Show tier names")
        self.target_times_toggle = QCheckBox("Label target start/end above figure")
        self.preview_size_mode = QComboBox()
        self.preview_size_mode.addItem("Fit to window", "fit")
        self.preview_size_mode.addItem("Real size", "real")
        self.preview_size_mode.currentIndexChanged.connect(self._preview_mode_changed)
        self.boundary_width = QDoubleSpinBox()
        self.boundary_width.setRange(0.25, 5.0)
        self.boundary_width.setDecimals(2)
        self.boundary_width.setSingleStep(0.25)
        self.boundary_width.setValue(1.1)
        self.boundary_width.valueChanged.connect(self.schedule_preview)
        self.spectrogram_dynamic_range = QDoubleSpinBox()
        self.spectrogram_dynamic_range.setRange(20.0, 120.0)
        self.spectrogram_dynamic_range.setDecimals(1)
        self.spectrogram_dynamic_range.setSingleStep(5.0)
        self.spectrogram_dynamic_range.setValue(70.0)
        self.spectrogram_dynamic_range.setToolTip(
            "Higher values retain more low-level detail and background noise."
        )
        self.spectrogram_preemphasis = QDoubleSpinBox()
        self.spectrogram_preemphasis.setRange(0.0, 1000.0)
        self.spectrogram_preemphasis.setDecimals(0)
        self.spectrogram_preemphasis.setSingleStep(10.0)
        self.spectrogram_preemphasis.setSpecialValueText("Off")
        self.spectrogram_preemphasis.setValue(50.0)
        self.spectrogram_preemphasis.setToolTip(
            "Praat-like +6 dB/octave display emphasis above this frequency."
        )
        self.spectrogram_compression = QDoubleSpinBox()
        self.spectrogram_compression.setRange(0.0, 1.0)
        self.spectrogram_compression.setDecimals(2)
        self.spectrogram_compression.setSingleStep(0.05)
        self.spectrogram_compression.setValue(0.25)
        self.spectrogram_compression.setToolTip(
            "Makes quiet time slices more visible; 0 is off and 1 fully normalizes them."
        )
        self.spectrogram_time_step = QDoubleSpinBox()
        self.spectrogram_time_step.setRange(0.25, 10.0)
        self.spectrogram_time_step.setDecimals(2)
        self.spectrogram_time_step.setSingleStep(0.25)
        self.spectrogram_time_step.setValue(1.0)
        self.spectrogram_time_step.setToolTip("Smaller values provide finer time detail.")
        self.spectrogram_frequency_step = QDoubleSpinBox()
        self.spectrogram_frequency_step.setRange(5.0, 250.0)
        self.spectrogram_frequency_step.setDecimals(1)
        self.spectrogram_frequency_step.setSingleStep(5.0)
        self.spectrogram_frequency_step.setValue(10.0)
        self.spectrogram_frequency_step.setToolTip("Smaller values provide finer frequency detail.")
        for control in (
            self.spectrogram_dynamic_range, self.spectrogram_preemphasis,
            self.spectrogram_compression, self.spectrogram_time_step,
            self.spectrogram_frequency_step,
        ):
            control.valueChanged.connect(self.schedule_preview)
        self.base_font_size = QDoubleSpinBox()
        self.annotation_font_size = QDoubleSpinBox()
        self.axis_font_size = QDoubleSpinBox()
        self.font_family = QComboBox()
        system_families = set(QFontDatabase.families())
        if not system_families:
            from matplotlib.font_manager import fontManager
            system_families = {font.name for font in fontManager.ttflist if font.name}
        self.font_family.addItems(sorted(system_families, key=str.casefold))
        default_font = self.font_family.findText("DejaVu Sans")
        self.font_family.setCurrentIndex(max(0, default_font))
        self.font_family.currentTextChanged.connect(self.schedule_preview)
        for control, value in (
            (self.base_font_size, 9.0),
            (self.annotation_font_size, 10.0),
            (self.axis_font_size, 6.0),
        ):
            control.setRange(5.0, 36.0)
            control.setDecimals(1)
            control.setSingleStep(0.5)
            control.setValue(value)
            control.valueChanged.connect(self.schedule_preview)
        for control in (self.time_ticks, self.time_label_toggle, self.wave_axis_toggle,
                        self.frequency_ticks_toggle, self.tier_names_toggle,
                        self.target_times_toggle):
            if isinstance(control, QComboBox):
                control.currentIndexChanged.connect(self.schedule_preview)
            else:
                control.toggled.connect(self.schedule_preview)
        display_row.addRow("Preview size", self.preview_size_mode)
        display_row.addRow("Time ticks", self.time_ticks)
        display_row.addRow(self.time_label_toggle)
        display_row.addRow(self.wave_axis_toggle)
        display_row.addRow(self.frequency_ticks_toggle)
        display_row.addRow(self.tier_names_toggle)
        display_row.addRow(self.target_times_toggle)
        display_row.addRow("Boundary width [pt]", self.boundary_width)
        display_row.addRow("Spectrogram dynamic range [dB]", self.spectrogram_dynamic_range)
        display_row.addRow("Spectrogram pre-emphasis from [Hz]", self.spectrogram_preemphasis)
        display_row.addRow("Spectrogram quiet-region normalization", self.spectrogram_compression)
        display_row.addRow("Spectrogram time step [ms]", self.spectrogram_time_step)
        display_row.addRow("Spectrogram frequency step [Hz]", self.spectrogram_frequency_step)
        display_row.addRow("Font family", self.font_family)
        display_row.addRow("Base font [pt]", self.base_font_size)
        display_row.addRow("Annotation font [pt]", self.annotation_font_size)
        display_row.addRow("Axis font [pt]", self.axis_font_size)
        layout.addLayout(display_row)
        nav = QHBoxLayout()
        previous = QPushButton("◀ Previous")
        following = QPushButton("Next ▶")
        previous.clicked.connect(lambda: self.move_selection(-1))
        following.clicked.connect(lambda: self.move_selection(1))
        nav.addWidget(previous)
        nav.addWidget(following)
        layout.addLayout(nav)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        scroll.setMinimumWidth(300)
        scroll.setMaximumWidth(400)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return scroll

    def open_audio(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open audio", "", "Audio (*.wav *.flac *.aiff *.mp3)")
        if not path:
            return
        try:
            self.audio = load_audio(path)
            self.audio_path = path
            self.audio_label.setText(f"Audio: {Path(path).name} ({self.audio.duration:.2f} s)")
            self._try_ready()
        except Exception as exc:
            self._error(str(exc))

    def open_textgrid(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open TextGrid", "", "Praat TextGrid (*.TextGrid *.textgrid)")
        if not path:
            return
        try:
            self.grid = load_textgrid(path)
            self.grid_path = path
            self.grid_label.setText(f"TextGrid: {Path(path).name}")
            self.tier_combo.clear()
            self.tier_combo.addItems([tier.name for tier in self.grid.tiers])
            self.target_tier_combo.clear()
            self.target_tier_combo.addItems([tier.name for tier in self.grid.tiers if tier.kind == "interval"])
            if self.audio is None:
                candidates = [Path(path).with_suffix(ext) for ext in (".wav", ".flac", ".aiff")]
                found = [candidate for candidate in candidates if candidate.exists()]
                if len(found) == 1:
                    self.audio = load_audio(found[0])
                    self.audio_path = str(found[0])
                    self.audio_label.setText(f"Audio: {found[0].name} ({self.audio.duration:.2f} s)")
            self.populate_table()
            self._try_ready()
        except Exception as exc:
            self._error(str(exc))

    def _try_ready(self) -> None:
        if not self.audio or not self.grid:
            return
        if self.spec is None:
            start = max(self.grid.xmin, self.audio.start_time)
            available_end = min(self.grid.xmax, self.audio.end_time)
            # Never analyse a long recording before the user has chosen an example.
            end = min(start + 10.0, available_end)
            self.spec = FigureSpec.publication(TimeRange(start, end), [],
                                                [t.name for t in self.grid.tiers if t.non_empty])
            self.manual_start.setValue(start)
            self.manual_end.setValue(end)
            self._reload_track_list()
        self.schedule_preview()

    def populate_table(self, *_args) -> None:
        if not self.grid or not self.tier_combo.currentText():
            return
        try:
            tier = self.grid.tier(self.tier_combo.currentText())
            query = self.search.text()
            self._entries = tier.search(query, self.search_mode.currentText()) if query else tier.entries
        except Exception as exc:
            self.status_label.setText(str(exc))
            return
        self.table.setRowCount(len(self._entries))
        for row, entry in enumerate(self._entries):
            values = [str(entry.index), entry.label, f"{entry.start:.3f}",
                      "—" if entry.end is None else f"{entry.end:.3f}",
                      "—" if entry.end is None else f"{entry.duration * 1000:.0f}"]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def select_row(self, index) -> None:
        if not self.spec or not self.grid:
            return
        entry = self._entries[index.row()]
        if entry.end is None:
            self.status_label.setText("Select an interval; point selections are shown as markers.")
            return
        self.spec.targets = [Target(entry.start, entry.end, self.tier_combo.currentText(), entry.index, entry.label)]
        self._source_range = TimeRange(entry.start, entry.end)
        self._source_label = entry.label.strip() or None
        self.spec.view_range = TimeRange(entry.start, entry.end).padded(
            self.left_padding.value(), self.right_padding.value(),
            minimum=self.grid.xmin, maximum=self.grid.xmax,
        )
        self.manual_start.setValue(self.spec.view_range.start)
        self.manual_end.setValue(self.spec.view_range.end)
        self._populate_target_entries()
        self.schedule_preview()

    def select_current_row(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            self.status_label.setText("Select an annotation row first.")
            return
        self.select_row(self.table.model().index(row, 0))

    def _populate_target_entries(self, *_args) -> None:
        self._updating_target_checks = True
        self.target_entries.clear()
        if not self.grid or not self.target_tier_combo.currentText():
            self._updating_target_checks = False
            return
        tier = self.grid.tier(self.target_tier_combo.currentText())
        bounds = self._source_range or (self.spec.view_range if self.spec else None)
        if bounds is None:
            self._updating_target_checks = False
            return
        current = {
            (target.tier, target.entry_index, round(target.start, 9), round(target.end, 9))
            for target in (self.spec.targets if self.spec else [])
        }
        for entry in tier.entries:
            if entry.end is None:
                continue
            if entry.start >= bounds.start - 1e-9 and entry.end <= bounds.end + 1e-9:
                label = entry.label or "(empty)"
                item = QListWidgetItem(f"{label}   {entry.start:.4f}–{entry.end:.4f}")
                item.setData(Qt.UserRole, entry)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                key = (tier.name, entry.index, round(entry.start, 9), round(entry.end, 9))
                item.setCheckState(Qt.Checked if key in current else Qt.Unchecked)
                self.target_entries.addItem(item)
        self._updating_target_checks = False

    def use_selected_targets(self) -> None:
        if not self.spec:
            return
        checked = [
            self.target_entries.item(index)
            for index in range(self.target_entries.count())
            if self.target_entries.item(index).checkState() == Qt.Checked
        ]
        if not checked:
            selected = self.target_entries.selectedItems()
            self._updating_target_checks = True
            for item in selected:
                item.setCheckState(Qt.Checked)
            self._updating_target_checks = False
        self._apply_checked_targets()

    def _target_checks_changed(self, *_args) -> None:
        if not self._updating_target_checks:
            self._apply_checked_targets()

    def _apply_checked_targets(self) -> None:
        if not self.spec:
            return
        checked = [
            self.target_entries.item(index)
            for index in range(self.target_entries.count())
            if self.target_entries.item(index).checkState() == Qt.Checked
        ]
        tier_name = self.target_tier_combo.currentText()
        self.spec.targets = [
            Target(item.data(Qt.UserRole).start, item.data(Qt.UserRole).end,
                   tier_name, item.data(Qt.UserRole).index, item.data(Qt.UserRole).label)
            for item in checked
        ]
        if checked:
            self.bounds_toggle.setChecked(True)
            self.spec.boundary_projection.mode = "target_only"
        self.schedule_preview()

    def clear_selected_targets(self) -> None:
        self._updating_target_checks = True
        for index in range(self.target_entries.count()):
            self.target_entries.item(index).setCheckState(Qt.Unchecked)
        self._updating_target_checks = False
        if self.spec:
            self.spec.targets = []
        self.schedule_preview()

    def use_manual_timespan(self) -> None:
        if not self.spec:
            return
        try:
            self.spec.view_range = TimeRange(self.manual_start.value(), self.manual_end.value())
            self.spec.targets = []
            self._source_range = self.spec.view_range
            self._source_label = None
            self._populate_target_entries()
            if self.time_mode.currentData() == "relative_to_target_start":
                self.time_mode.setCurrentIndex(0)
            self.schedule_preview()
        except ValueError as exc:
            self._error(str(exc))

    def move_selection(self, delta: int) -> None:
        row = self.table.currentRow()
        row = max(0, min(self.table.rowCount() - 1, row + delta))
        if row >= 0:
            self.table.selectRow(row)
            self.select_row(self.table.model().index(row, 0))

    def _reload_track_list(self) -> None:
        self.tracks.blockSignals(True)
        self.tracks.clear()
        if not self.spec:
            self.tracks.blockSignals(False)
            return
        for index, track in enumerate(self.spec.tracks):
            default_label = track.kind.title() if not isinstance(track, AnnotationTrack) else track.tier
            label = track.display_name or default_label
            item = QTreeWidgetItem(["", label, f"{track.height:.2f}"])
            item.setData(0, Qt.UserRole, index)
            flags = item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable | Qt.ItemIsDragEnabled
            item.setFlags(flags & ~Qt.ItemIsDropEnabled)
            item.setCheckState(0, Qt.Checked if track.visible else Qt.Unchecked)
            item.setToolTip(1, "Double-click to rename this layer on the exported figure")
            item.setToolTip(2, "Relative layer height; for example 0.5, 1.0, or 2.0")
            self.tracks.addTopLevelItem(item)
        self.tracks.blockSignals(False)

    def _track_selected(self, current, _previous) -> None:
        if not current or not self.spec:
            return
        index = current.data(0, Qt.UserRole)
        if index is None or index >= len(self.spec.tracks):
            return
        self.track_height.blockSignals(True)
        try:
            value = float(current.text(2))
        except ValueError:
            value = self.spec.tracks[index].height
        self.track_height.setValue(value)
        self.track_height.blockSignals(False)

    def _set_selected_track_height(self, value: float) -> None:
        item = self.tracks.currentItem()
        if not item or not self.spec:
            return
        index = item.data(0, Qt.UserRole)
        if index is not None and index < len(self.spec.tracks):
            self.spec.tracks[index].height = value
            self.tracks.blockSignals(True)
            item.setText(2, f"{value:.2f}")
            self.tracks.blockSignals(False)
            self.schedule_preview()

    def _apply_controls(self) -> None:
        if not self.spec:
            return
        items = [self.tracks.topLevelItem(i) for i in range(self.tracks.topLevelItemCount())]
        order = [item.data(0, Qt.UserRole) for item in items]
        if len(order) == len(self.spec.tracks):
            reordered = []
            for row, index in enumerate(order):
                track = self.spec.tracks[index]
                item = items[row]
                track.visible = item.checkState(0) == Qt.Checked
                default_label = track.kind.title() if not isinstance(track, AnnotationTrack) else track.tier
                edited_label = item.text(1).strip()
                track.display_name = edited_label if edited_label and edited_label != default_label else None
                try:
                    track.height = min(5.0, max(0.2, float(item.text(2).replace(",", "."))))
                except ValueError:
                    item.setText(2, f"{track.height:.2f}")
                reordered.append(track)
            self.spec.tracks = reordered
            self._reload_track_list()
        self.spec.time_mode = self.time_mode.currentData()
        self.spec.boundary_projection.mode = "target_only" if self.bounds_toggle.isChecked() else "none"
        self.spec.duration.visible = self.duration_toggle.isChecked()
        self.spec.boundary_projection.label_target_times = self.target_times_toggle.isChecked()
        self.spec.boundary_projection.line_width = self.boundary_width.value()
        self.spec.appearance.base_font_size = self.base_font_size.value()
        self.spec.appearance.annotation_font_size = self.annotation_font_size.value()
        self.spec.appearance.axis_font_size = self.axis_font_size.value()
        self.spec.appearance.font_family = self.font_family.currentText()
        self.spec.x_ticks_mode = self.time_ticks.currentData()
        self.spec.show_x_axis = self.time_ticks.currentData() != "hidden"
        self.spec.show_time_label = self.time_label_toggle.isChecked()
        for track in self.spec.tracks:
            if isinstance(track, WaveformTrack):
                track.show_y_ticks = self.wave_axis_toggle.isChecked()
                track.show_y_label = self.wave_axis_toggle.isChecked()
            elif isinstance(track, SpectrogramTrack):
                track.pitch = self.pitch_toggle.isChecked()
                track.formants = [1, 2] if self.formant_toggle.isChecked() else []
                track.show_frequency_ticks = self.frequency_ticks_toggle.isChecked()
                track.dynamic_range = self.spectrogram_dynamic_range.value()
                track.preemphasis_from = self.spectrogram_preemphasis.value()
                track.dynamic_compression = self.spectrogram_compression.value()
                track.time_step = self.spectrogram_time_step.value() / 1000.0
                track.frequency_step = self.spectrogram_frequency_step.value()
            elif isinstance(track, AnnotationTrack):
                track.show_tier_name = "left" if self.tier_names_toggle.isChecked() else "hidden"

    def schedule_preview(self, *_args) -> None:
        if hasattr(self, "_timer"):
            self._timer.start()

    def schedule_preview_immediate(self, *_args) -> None:
        if hasattr(self, "_timer"):
            self._timer.start(0)

    def refresh_preview(self) -> None:
        if not self.audio or not self.grid or not self.spec:
            return
        try:
            self._apply_controls()
            self._render_generation += 1
            if self._render_busy:
                self._rerender_pending = True
                self.status_label.setText("Preview parameters changed — waiting for current analysis…")
                return
            generation = self._render_generation
            job = _RenderJob(generation, self.renderer, self.audio, self.grid, deepcopy(self.spec))
            job.signals.ready.connect(self._accept_render)
            job.signals.failed.connect(self._render_failed)
            job.signals.finished.connect(lambda token, current=job: self._render_finished(token, current))
            self._render_jobs.add(job)
            self._render_busy = True
            self.status_label.setText(
                f"Calculating preview for {self.spec.view_range.duration:.2f} s…"
            )
            self._render_pool.start(job)
        except Exception as exc:
            self._error(str(exc))

    def _accept_render(self, generation: int, figure) -> None:
        if generation != self._render_generation:
            plt.close(figure)
            return
        old = self.canvas.figure
        figure._praatfigure_real_size_inches = tuple(figure.get_size_inches())
        self.canvas.figure = figure
        figure.set_canvas(self.canvas)
        if old is not figure:
            plt.close(old)
        self.current_figure = figure
        self._apply_preview_scale()
        if self.spec:
            self.status_label.setText(
                f"View {self.spec.view_range.start:.3f}–{self.spec.view_range.end:.3f} s"
            )

    def _preview_mode_changed(self, *_args) -> None:
        self._apply_preview_scale()

    def _apply_preview_scale(self) -> None:
        if self.current_figure is None or not hasattr(self, "preview_scroll"):
            return
        figure = self.current_figure
        inches = getattr(figure, "_praatfigure_real_size_inches", tuple(figure.get_size_inches()))
        screen = self.screen() or QApplication.primaryScreen()
        logical_dpi = float(screen.logicalDotsPerInch()) if screen else 96.0
        real_width = inches[0] * logical_dpi
        real_height = inches[1] * logical_dpi
        if self.preview_size_mode.currentData() == "real":
            scale = 1.0
        else:
            viewport = self.preview_scroll.viewport().size()
            available_width = max(100.0, viewport.width() - 8.0)
            available_height = max(100.0, viewport.height() - 8.0)
            scale = max(0.05, min(available_width / real_width, available_height / real_height))
        display_width = max(1, round(real_width * scale))
        display_height = max(1, round(real_height * scale))
        pixel_ratio = self.canvas.devicePixelRatioF()
        figure.set_dpi(logical_dpi * pixel_ratio * scale)
        figure.set_size_inches(inches[0], inches[1], forward=False)
        self.canvas.setFixedSize(display_width, display_height)
        self.canvas.draw_idle()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.current_figure is not None and hasattr(self, "preview_size_mode"):
            QTimer.singleShot(0, self._apply_preview_scale)

    def _render_failed(self, generation: int, message: str) -> None:
        if generation == self._render_generation:
            self._error(message)

    def _render_finished(self, _generation: int, job: _RenderJob) -> None:
        self._render_jobs.discard(job)
        self._render_busy = False
        if self._rerender_pending:
            self._rerender_pending = False
            self._timer.start(0)

    def export(self) -> None:
        if not self.audio or not self.grid or not self.spec:
            return
        if self._render_busy:
            self.status_label.setText("Wait for the current preview before exporting.")
            return
        default_directory = self._last_export_directory or str(Path(self.audio_path).parent)
        dialog = ExportDialog(self, default_directory, self._default_export_name())
        if dialog.exec() != QDialog.Accepted:
            return
        destination = dialog.destination()
        overwrite = False
        if destination.exists():
            answer = QMessageBox.question(
                self, "Replace file?", f"{destination} already exists. Replace it?"
            )
            if answer != QMessageBox.Yes:
                return
            overwrite = True
        try:
            self._apply_controls()
            export_spec = deepcopy(self.spec)
            export_spec.appearance.dpi = int(dialog.dpi.value())
            # Export from an independent Figure. Saving the live Qt canvas can
            # replace its renderer and used to break subsequent previews.
            figure = self.renderer.render(self.audio, self.grid, export_spec)
            try:
                export_figure(
                    figure, destination, dpi=export_spec.appearance.dpi,
                    transparent=dialog.transparent.isChecked(), overwrite=overwrite,
                )
            finally:
                plt.close(figure)
            self._last_export_directory = str(destination.parent)
            self.status_label.setText(f"Exported {destination}")
        except Exception as exc:
            self._error(str(exc))

    def _default_export_name(self) -> str:
        audio_name = Path(self.audio_path).stem if self.audio_path else "figure"
        label = self._source_label
        if not label and self.spec:
            label = f"{self.spec.view_range.start:.3f}-{self.spec.view_range.end:.3f}"
        label = unicodedata.normalize("NFC", label or "figure")
        return sanitise_filename(f"{audio_name}_{label}")

    def save_template(self) -> None:
        if not self.spec:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save settings template", "publication.praatfig-template.json",
            "PraatFigure templates (*.praatfig-template.json)",
        )
        if not path:
            return
        try:
            self._apply_controls()
            style = self.spec.to_dict()
            style.pop("view_range", None)
            style.pop("targets", None)
            Path(path).write_text(
                json.dumps({"schema_version": 1, "figure_style": style}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.status_label.setText(f"Saved settings template {path}")
        except Exception as exc:
            self._error(str(exc))

    def load_template(self) -> None:
        if not self.spec:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Load settings template", "", "PraatFigure templates (*.praatfig-template.json)",
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            style = dict(data["figure_style"])
            style["view_range"] = {
                "start": self.spec.view_range.start,
                "end": self.spec.view_range.end,
            }
            style["targets"] = [target.to_dict() for target in self.spec.targets]
            self.spec = FigureSpec.from_dict(style)
            self._sync_controls_from_spec()
            self.schedule_preview()
            self.status_label.setText(f"Loaded settings template {path}")
        except Exception as exc:
            self._error(str(exc))

    def _sync_controls_from_spec(self) -> None:
        if not self.spec:
            return
        mode_index = self.time_mode.findData(self.spec.time_mode)
        self.time_mode.setCurrentIndex(max(0, mode_index))
        ticks_index = self.time_ticks.findData(self.spec.x_ticks_mode)
        self.time_ticks.setCurrentIndex(max(0, ticks_index))
        self.time_label_toggle.setChecked(self.spec.show_time_label)
        self.target_times_toggle.setChecked(self.spec.boundary_projection.label_target_times)
        self.boundary_width.setValue(self.spec.boundary_projection.line_width)
        self.bounds_toggle.setChecked(self.spec.boundary_projection.mode != "none")
        self.duration_toggle.setChecked(self.spec.duration.visible)
        self.base_font_size.setValue(self.spec.appearance.base_font_size)
        self.annotation_font_size.setValue(self.spec.appearance.annotation_font_size)
        self.axis_font_size.setValue(self.spec.appearance.axis_font_size)
        font_index = self.font_family.findText(self.spec.appearance.font_family)
        if font_index >= 0:
            self.font_family.setCurrentIndex(font_index)
        wave_tracks = [track for track in self.spec.tracks if isinstance(track, WaveformTrack)]
        spectrogram_tracks = [track for track in self.spec.tracks if isinstance(track, SpectrogramTrack)]
        annotation_tracks = [track for track in self.spec.tracks if isinstance(track, AnnotationTrack)]
        self.pitch_toggle.setChecked(any(track.pitch for track in spectrogram_tracks))
        self.formant_toggle.setChecked(any(track.formants for track in spectrogram_tracks))
        self.wave_axis_toggle.setChecked(any(track.show_y_ticks or track.show_y_label for track in wave_tracks))
        self.frequency_ticks_toggle.setChecked(
            any(track.show_frequency_ticks for track in spectrogram_tracks)
        )
        if spectrogram_tracks:
            spectrogram = spectrogram_tracks[0]
            self.spectrogram_dynamic_range.setValue(spectrogram.dynamic_range)
            self.spectrogram_preemphasis.setValue(spectrogram.preemphasis_from)
            self.spectrogram_compression.setValue(spectrogram.dynamic_compression)
            self.spectrogram_time_step.setValue(spectrogram.time_step * 1000.0)
            self.spectrogram_frequency_step.setValue(spectrogram.frequency_step)
        self.tier_names_toggle.setChecked(
            any(track.show_tier_name != "hidden" for track in annotation_tracks)
        )
        self._reload_track_list()

    def save_project(self) -> None:
        if not self.spec or not self.audio_path or not self.grid_path:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save project", "example.praatfig.json",
                                               "PraatFigure projects (*.praatfig.json)")
        if path:
            try:
                self._apply_controls()
                Project(self.audio_path, self.grid_path, self.spec).save(path)
                self.status_label.setText(f"Saved project {path}")
            except Exception as exc:
                self._error(str(exc))

    def open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open project", "",
                                               "PraatFigure projects (*.praatfig.json)")
        if not path:
            return
        try:
            project = Project.load(path)
            self.audio = load_audio(project.audio_path)
            self.grid = load_textgrid(project.textgrid_path)
            self.audio_path = project.audio_path
            self.grid_path = project.textgrid_path
            self.spec = project.figure_spec
            self.audio_label.setText(f"Audio: {Path(self.audio_path).name} ({self.audio.duration:.2f} s)")
            self.grid_label.setText(f"TextGrid: {Path(self.grid_path).name}")
            self.tier_combo.clear()
            self.tier_combo.addItems([tier.name for tier in self.grid.tiers])
            self.target_tier_combo.clear()
            self.target_tier_combo.addItems([tier.name for tier in self.grid.tiers if tier.kind == "interval"])
            self.manual_start.setValue(self.spec.view_range.start)
            self.manual_end.setValue(self.spec.view_range.end)
            self._source_range = self.spec.view_range
            self._source_label = self.spec.targets[0].label if self.spec.targets else None
            self._sync_controls_from_spec()
            self.populate_table()
            self._populate_target_entries()
            self.schedule_preview()
        except Exception as exc:
            self._error(str(exc))

    def _error(self, message: str) -> None:
        self.status_label.setText(message)
        QMessageBox.critical(self, "PraatFigure", message)

    def show_help(self) -> None:
        QMessageBox.information(
            self,
            "PraatFigure quick start",
            "1. Open the audio file and its TextGrid.\n"
            "2. Choose a tier, select an annotation row, and press “Render selected interval”.\n"
            "3. To project only an internal segment, choose its tier under “Target boundaries”, "
            "select one or more entries, and press “Project selected boundaries”.\n\n"
            "Tracks table:\n"
            "• Show — include or exclude the layer.\n"
            "• Name on figure — double-click to rename without modifying the TextGrid.\n"
            "• Height — double-click and enter a relative height (1 means equal height).\n"
            "Rows can be dragged between other rows to change their order.\n\n"
            "Preview size:\n"
            "• Fit to window scales the complete final figure, including fonts, pitch/formant "
            "markers, and line widths.\n"
            "• Real size uses the physical width and height configured for export; scroll if needed.\n\n"
            "Display controls choose endpoint/automatic time ticks, Hz ticks, tier names, "
            "target start/end labels, projected-boundary width, and separate "
            "base/annotation/axis font sizes plus any installed system font. Internal target "
            "annotations have independent "
            "checkboxes; uncheck one or use Clear projected boundaries to remove projection.\n\n"
            "Duration is independent: turn on Duration while leaving Boundary lines and "
            "Label target start/end off to show only the duration value.\n\n"
            "Spectrogram controls adjust low-level detail (dynamic range), Praat-like "
            "pre-emphasis, quiet-region normalization, and time/frequency grid detail. "
            "These settings change only the visualization, never the audio file.\n\n"
            "Export opens a dialog for filename, SVG/PDF/PNG format, DPI, and transparency. "
            "Use the Templates menu to save or apply all visual settings without changing "
            "the current annotation selection.",
        )


def launch() -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    return application.exec()
