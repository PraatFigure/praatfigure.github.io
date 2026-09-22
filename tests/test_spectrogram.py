import numpy as np

from praatfigure.analysis.acoustics import spectrogram
from praatfigure.io.audio import AudioData


def test_publication_spectrogram_has_fine_time_and_frequency_grid():
    sample_rate = 16000
    times = np.arange(sample_rate) / sample_rate
    audio = AudioData(np.sin(2 * np.pi * 220 * times), sample_rate)
    frequencies, frame_times, power = spectrogram(audio, 0.0, 1.0)
    assert power.shape == (len(frequencies), len(frame_times))
    # Praat may quantize the requested 20 Hz step to a nearby FFT-compatible grid.
    assert np.median(np.diff(frequencies)) <= 35.0
    assert np.median(np.diff(frame_times)) <= 0.0021
