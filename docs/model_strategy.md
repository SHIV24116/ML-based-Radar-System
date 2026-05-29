# Model Strategy

## Final Demo Choice

Use supervised classification for the final project demo. The classes are known
beforehand, and the system will collect labeled recordings such as `human`,
`fan`, and `background`.

The comparison script automatically selects the best supervised model from:

- RBF SVM
- Linear SVM
- Random Forest
- Extra Trees
- Gradient Boosting
- K-Nearest Neighbors
- Logistic Regression
- Gaussian Naive Bayes

The selected model is saved as `models/best_supervised_model.pkl`.

## Unsupervised Models

Unsupervised models are included for analysis, not as the main final demo path.
They are useful for checking whether recordings naturally form clusters and for
spotting unknown or badly recorded samples.

Compared methods:

- K-Means
- Gaussian Mixture
- Agglomerative Clustering
- DBSCAN

## Important Project Claim

Do not claim final accuracy from simulated data. Simulated data is only for
software validation while the circuit is pending. Final reported accuracy should
come from real recordings collected through the CDM324, MCP6002 conditioning
circuit, and ESP32 ADC.
