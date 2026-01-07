# Needs improvement: Timestamp consistency , Buffering protection


import numpy as np

signal = np.loadtxt("recording.csv")

# Convert ADC to voltage (optional but recommended)
signal = signal * (3.3 / 4095)

# DC removal
signal = signal - np.mean(signal)

from scipy.signal import butter, filtfilt

fs = 2000  # sampling frequency

b, a = butter(
    4,
    [10/(fs/2), 500/(fs/2)],
    btype='band'
)

filtered = filtfilt(b, a, signal)

# Sanity check code

import matplotlib.pyplot as plt

fft_vals = np.abs(np.fft.fft(filtered))
freqs = np.fft.fftfreq(len(fft_vals), 1/fs)

plt.plot(freqs[:len(freqs)//2], fft_vals[:len(fft_vals)//2])
plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude")
plt.show()

# Micro-Doppler Extraction

from scipy.signal import stft

f, t, Zxx = stft(filtered, fs=fs, nperseg=256, noverlap=128)
spectrogram = np.abs(Zxx)
