# ML Pipeline

## Recommended Model Choice

For the final demo, use the best supervised model selected by
`ML/compare_models.py`. Supervised models are the right fit because the project
will collect labeled recordings such as `human`, `fan`, and `background`.

Unsupervised models are still included because they help with:

- checking whether classes naturally separate,
- discovering strange or unknown recordings,
- validating that the feature space is meaningful.

## Compare Models

With simulated data:

```powershell
python "Simulation/generate_synthetic_dataset.py" --recordings-per-class 30
python "ML/compare_models.py" --dataset dataset_simulated
```

With real circuit data later:

```powershell
python "ML/compare_models.py" --dataset dataset
```

Outputs are written to `outputs/model_comparison/`, and the best supervised
model is saved to `models/best_supervised_model.pkl`.
