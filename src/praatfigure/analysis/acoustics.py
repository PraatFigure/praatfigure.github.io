from __future__ import annotations

import numpy as np
from scipy import signal

from ..io.audio import AudioData


def spectrogram(audio: AudioData, start: float, end: float, *, window_length: float = 0.005,
                maximum_frequency: float = 5000.0, dynamic_range: float = 70.0,
                time_step: float = 0.001, frequency_step: float = 10.0,
                preemphasis_from: float = 50.0,
                dynamic_compression: float = 0.0):
    # Include enough context for the first and last analysis windows to reach
    # the requested view boundaries. The renderer crops the padded frames.
    analysis_start = max(audio.start_time, start - window_length)
    analysis_end = min(audio.end_time, end + window_length)
    _, values = audio.window(analysis_start, analysis_end)
    if len(values) < 2:
        raise ValueError("Selected audio range is too short for a spectrogram")
    try:
        sound = _parselmouth_sound(audio, analysis_start, analysis_end)
        obj = sound.to_spectrogram(
            window_length=window_length,
            maximum_frequency=maximum_frequency,
            time_step=time_step,
            frequency_step=frequency_step,
        )
        power = np.asarray(obj.values, dtype=float)
        db = _prepare_spectrogram_db(
            power, obj.ys(), dynamic_range, preemphasis_from, dynamic_compression
        )
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
    keep = frequencies <= maximum_frequency
    frequencies = frequencies[keep]
    db = _prepare_spectrogram_db(
        power[keep], frequencies, dynamic_range, preemphasis_from, dynamic_compression
    )
    return frequencies, times + analysis_start, db


def _prepare_spectrogram_db(power: np.ndarray, frequencies: np.ndarray,
                            dynamic_range: float, preemphasis_from: float,
                            dynamic_compression: float) -> np.ndarray:
    """Apply Praat-like display emphasis and intensity normalization."""
    db = 10 * np.log10(np.maximum(power, np.finfo(float).tiny))
    if preemphasis_from > 0:
        # A first-order high-pass display curve: approximately +6 dB/octave
        # above the selected frequency, without modifying the source audio.
        emphasis = 10 * np.log10(1.0 + (frequencies / preemphasis_from) ** 2)
        db = db + emphasis[:, np.newaxis]
    compression = float(np.clip(dynamic_compression, 0.0, 1.0))
    if compression and db.shape[1]:
        local_peak = np.nanmax(db, axis=0)
        global_peak = float(np.nanmax(local_peak))
        db = db + compression * (global_peak - local_peak)[np.newaxis, :]
    maximum = float(np.nanmax(db))
    return np.maximum(db, maximum - max(1.0, dynamic_range))


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
