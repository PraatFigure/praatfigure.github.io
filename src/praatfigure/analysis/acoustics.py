from __future__ import annotations

import numpy as np
from scipy import signal

from ..io.audio import AudioData


def spectrogram(audio: AudioData, start: float, end: float, *, window_length: float = 0.005,
                maximum_frequency: float = 5000.0, dynamic_range: float = 70.0,
                time_step: float = 0.002, frequency_step: float = 20.0):
    _, values = audio.window(start, end)
    if len(values) < 2:
        raise ValueError("Selected audio range is too short for a spectrogram")
    try:
        sound = _parselmouth_sound(audio, start, end)
        obj = sound.to_spectrogram(
            window_length=window_length,
            maximum_frequency=maximum_frequency,
            time_step=time_step,
            frequency_step=frequency_step,
        )
        power = np.asarray(obj.values, dtype=float)
        db = 10 * np.log10(np.maximum(power, np.finfo(float).tiny))
        db = np.maximum(db, np.nanmax(db) - dynamic_range)
        return obj.ys(), obj.xs(), db
    except ImportError:
        pass
    except RuntimeError as exc:
        if "praat-parselmouth" not in str(exc):
            raise

    # Dependency-light fallback with Praat-like time/frequency sampling.
    nperseg = max(16, int(round(window_length * audio.sample_rate)))
    nperseg = min(nperseg, max(1, len(values)))
    hop = max(1, int(round(time_step * audio.sample_rate)))
    nfft = max(nperseg, int(np.ceil(audio.sample_rate / max(1.0, frequency_step))))
    nfft = 1 << (nfft - 1).bit_length()
    window = signal.windows.gaussian(nperseg, std=max(1.0, nperseg / 6.0))
    frequencies, times, power = signal.spectrogram(
        values, fs=audio.sample_rate, window=window, nperseg=nperseg, nfft=nfft,
        noverlap=max(0, nperseg - hop), mode="psd",
    )
    db = 10 * np.log10(np.maximum(power, np.finfo(float).tiny))
    db = np.maximum(db, np.nanmax(db) - dynamic_range)
    keep = frequencies <= maximum_frequency
    return frequencies[keep], times + start, db[keep]


def _parselmouth_sound(audio: AudioData, start: float, end: float):
    try:
        import parselmouth
    except ImportError as exc:
        raise RuntimeError("Pitch and formants require praat-parselmouth") from exc
    _, values = audio.window(start, end)
    return parselmouth.Sound(values, sampling_frequency=audio.sample_rate, start_time=start)


def pitch(audio: AudioData, start: float, end: float, floor: float = 75.0,
          ceiling: float = 600.0) -> tuple[np.ndarray, np.ndarray]:
    sound = _parselmouth_sound(audio, start, end)
    obj = sound.to_pitch_ac(pitch_floor=floor, pitch_ceiling=ceiling)
    times = obj.xs()
    values = obj.selected_array["frequency"].astype(float)
    values[values <= 0] = np.nan
    return times, values


def formants(audio: AudioData, start: float, end: float, indices: list[int],
             ceiling: float = 5500.0) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    sound = _parselmouth_sound(audio, start, end)
    obj = sound.to_formant_burg(max_number_of_formants=max(indices, default=2) + 1,
                                maximum_formant=ceiling)
    times = obj.xs()
    result = {}
    for index in indices:
        values = np.array([obj.get_value_at_time(index, time) for time in times], dtype=float)
        result[index] = (times, values)
    return result
