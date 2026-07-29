# ML Model Report

## Current Pipeline

1. Load raw radar CSV recordings.
2. Convert ADC values to voltage when needed.
3. Remove DC and apply a band-pass filter.
4. Extract radar-only time, FFT, STFT, and spectral features.
5. Compare supervised and unsupervised models.
6. Save the best supervised model to `models/best_supervised_model.pkl`.

## Feature Set

The feature table contains radar-only values such as spectrogram statistics, dominant Doppler frequency, spectral centroid, spectral bandwidth, band-energy ratios, mean, variance, RMS, signal energy, spectral entropy, peak width, zero-crossing rate, maximum, minimum, and signal range.

Distance, ultrasonic speed, object presence, and motion direction are excluded from model input.

## Training Command

```powershell
python "ML/compare_models.py" --dataset dataset
```

For software-only testing:

```powershell
python "Simulation/generate_synthetic_dataset.py" --recordings-per-class 30
python "ML/compare_models.py" --dataset dataset_simulated
```

## Outputs

- `outputs/model_comparison/feature_table.csv`
- `outputs/model_comparison/supervised_results.csv`
- `outputs/model_comparison/unsupervised_results.csv`
- `outputs/model_comparison/supervised_reports.json`
- `outputs/model_comparison/summary.json`
- `outputs/model_comparison/plots/best_confusion_matrix.png`
- `models/best_supervised_model.pkl`

## Final Deployment Note

The included firmware has a complete inference wrapper and a hardware bring-up fallback. For final TFLite Micro deployment, export the trained model to `Models/model.tflite`, convert it to a C array, and connect it inside `Firmware/MLInference.cpp`.
