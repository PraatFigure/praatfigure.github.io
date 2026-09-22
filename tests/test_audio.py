import numpy as np
from scipy.io import wavfile

from praatfigure.io.audio import load_audio


def test_audio_is_file_backed_and_reads_only_requested_window(tmp_path):
    sample_rate = 16000
    samples = (np.sin(2 * np.pi * 220 * np.arange(sample_rate * 2) / sample_rate) * 16000).astype(np.int16)
    path = tmp_path / "large-enough.wav"
    wavfile.write(path, sample_rate, samples)

    audio = load_audio(path)

    assert audio.is_file_backed
    assert audio.duration == 2.0
    times, values = audio.window(0.5, 0.6)
    assert len(values) == 1600
    assert times[0] == 0.5
    assert np.max(np.abs(values)) <= 1.0
