# Simulation

Use this folder when the hardware circuit is not ready. The generator creates
realistic-enough CSV files to test the DSP and ML software pipeline.

```powershell
python "Simulation/generate_synthetic_dataset.py" --recordings-per-class 30
```

The default output is `dataset_simulated/`.

Important: simulated data is only for software validation. Final model results
must be retrained on real radar recordings from the circuit.
