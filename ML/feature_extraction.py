import numpy as np

def extract_features(spec):
    return [
        np.mean(spec),
        np.std(spec),
        np.max(spec),
        np.sum(spec)
    ]
