from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(slots=True)
class AudioData:
    samples: np.ndarray | None
    sample_rate: int
    start_time: float = 0.0
    path: str | None = None
    frame_count: int | None = None
    channels: int = 1

    @property
    def duration(self) -> float:
        frames = self.frame_count if self.frame_count is not None else len(self.samples)  # type: ignore[arg-type]
        return frames / self.sample_rate

    @property
    def end_time(self) -> float:
        return self.start_time + self.duration

    @property
    def is_file_backed(self) -> bool:
        return self.samples is None or isinstance(self.samples, np.memmap)

    def _select_channel(self, samples: np.ndarray, channel: str = "average") -> np.ndarray:
        if samples.ndim == 1:
            return samples
        if channel == "separate":
            return samples
        if channel == "left":
            return samples[:, 0]
        if channel == "right":
            return samples[:, min(1, samples.shape[1] - 1)]
        return samples.mean(axis=1)

    def window(self, start: float, end: float, channel: str = "average") -> tuple[np.ndarray, np.ndarray]:
        first = max(0, int(round((start - self.start_time) * self.sample_rate)))
        total = self.frame_count if self.frame_count is not None else len(self.samples)  # type: ignore[arg-type]
        last = min(total, int(round((end - self.start_time) * self.sample_rate)))
        if last <= first:
            return np.array([], dtype=float), np.array([], dtype=float)
        if self.samples is None:
            if not self.path:
                raise RuntimeError("File-backed audio has no source path")
            try:
                import soundfile as sf
            except ImportError as exc:
                raise RuntimeError("Reading this audio window requires soundfile") from exc
            with sf.SoundFile(self.path) as source:
                source.seek(first)
                chunk = source.read(last - first, dtype="float64", always_2d=False)
        else:
            # A WAV loaded with mmap=True reaches disk only for this slice.
            chunk = _normalise_pcm(np.asarray(self.samples[first:last]))
        values = self._select_channel(np.asarray(chunk), channel)
        times = self.start_time + np.arange(first, last) / self.sample_rate
        return times, values


def _normalise_pcm(data: np.ndarray) -> np.ndarray:
    if np.issubdtype(data.dtype, np.integer):
        info = np.iinfo(data.dtype)
        scale = max(abs(info.min), info.max)
        return data.astype(np.float64) / scale
    return data.astype(np.float64, copy=False)


def load_audio(path: str | Path) -> AudioData:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    try:
        import soundfile as sf
        info = sf.info(source)
        return AudioData(
            samples=None,
            sample_rate=int(info.samplerate),
            path=str(source),
            frame_count=int(info.frames),
            channels=int(info.channels),
        )
    except ImportError:
        if source.suffix.lower() != ".wav":
            raise RuntimeError("Non-WAV audio requires the optional soundfile dependency")
        from scipy.io import wavfile
        sample_rate, samples = wavfile.read(source, mmap=True)
        channels = 1 if samples.ndim == 1 else int(samples.shape[1])
        return AudioData(samples, int(sample_rate), path=str(source),
                         frame_count=len(samples), channels=channels)
