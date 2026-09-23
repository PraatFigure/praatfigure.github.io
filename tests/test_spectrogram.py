import numpy as np

from praatfigure.analysis.acoustics import spectrogram
from praatfigure.io.audio import AudioData


def test_publication_spectrogram_has_fine_time_and_frequency_grid():
    sample_rate = 16000
    times = np.arange(sample_rate) / sample_rate
    audio = AudioData(np.sin(2 * np.pi * 220 * times), sample_rate)
    frequencies, frame_times, power = spectrogram(audio, 0.0, 1.0)
    assert power.shape == (len(frequencies), len(frame_times))
    # Praat quantizes the requested step to its nearest FFT-compatible grid.
    assert np.median(np.diff(frequencies)) <= 35.0
    assert np.median(np.diff(frame_times)) <= 0.0011


def test_dynamic_compression_reduces_frame_peak_variation():
    sample_rate = 16000
    times = np.arange(sample_rate) / sample_rate
    envelope = np.where(times < 0.5, 0.05, 1.0)
    audio = AudioData(envelope * np.sin(2 * np.pi * 220 * times), sample_rate)
    _, _, uncompressed = spectrogram(audio, 0.0, 1.0, dynamic_compression=0.0)
    _, _, compressed = spectrogram(audio, 0.0, 1.0, dynamic_compression=1.0)
    assert np.ptp(np.max(compressed, axis=0)) < np.ptp(np.max(uncompressed, axis=0))


def test_preemphasis_strengthens_high_frequencies_relative_to_low():
    sample_rate = 16000
    times = np.arange(sample_rate) / sample_rate
    samples = np.sin(2 * np.pi * 200 * times) + np.sin(2 * np.pi * 3000 * times)
    audio = AudioData(samples, sample_rate)
    frequencies, _, plain = spectrogram(audio, 0.0, 1.0, preemphasis_from=0.0)
    _, _, emphasised = spectrogram(audio, 0.0, 1.0, preemphasis_from=50.0)
    low = int(np.argmin(np.abs(frequencies - 200)))
    high = int(np.argmin(np.abs(frequencies - 3000)))
    plain_difference = np.max(plain[high]) - np.max(plain[low])
    emphasised_difference = np.max(emphasised[high]) - np.max(emphasised[low])
    assert emphasised_difference > plain_difference + 10
