"""Compare supervised and unsupervised ML models for radar classification.

This script is the main offline experiment runner. It can use either real data
from `dataset/` or simulated data from `dataset_simulated/`.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, DBSCAN, KMeans
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    adjusted_rand_score,
    calinski_harabasz_score,
    classification_report,
    confusion_matrix,
    davies_bouldin_score,
    f1_score,
    normalized_mutual_info_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ML_DIR = Path(__file__).resolve().parent
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from feature_extraction import FEATURE_NAMES  # noqa: E402
from train_svm import build_feature_table  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare radar ML models.")
    parser.add_argument("--dataset", default="dataset_simulated", help="Dataset root folder.")
    parser.add_argument("--fs", type=float, default=2000.0, help="Sampling frequency in Hz.")
    parser.add_argument("--test-size", type=float, default=0.25, help="Holdout test fraction.")
    parser.add_argument("--output-dir", default="outputs/model_comparison", help="Experiment output folder.")
    parser.add_argument("--model-out", default="models/best_supervised_model.pkl", help="Best model output path.")
    parser.add_argument("--random-state", type=int, default=42, help="Random seed.")
    return parser.parse_args()


def supervised_models(random_state: int) -> dict[str, object]:
    return {
        "svm_rbf": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", SVC(kernel="rbf", C=10.0, gamma="scale", probability=True, class_weight="balanced")),
            ]
        ),
        "svm_linear": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", SVC(kernel="linear", probability=True, class_weight="balanced")),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=250,
            class_weight="balanced",
            random_state=random_state,
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=250,
            class_weight="balanced",
            random_state=random_state,
        ),
        "gradient_boosting": GradientBoostingClassifier(random_state=random_state),
        "knn": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", KNeighborsClassifier(n_neighbors=5)),
            ]
        ),
        "logistic_regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(max_iter=2000, class_weight="balanced")),
            ]
        ),
        "gaussian_nb": GaussianNB(),
    }


def compare_supervised(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float,
    random_state: int,
) -> tuple[pd.DataFrame, dict[str, object], dict[str, object]]:
    stratify = y if y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )

    min_class_count = int(y_train.value_counts().min())
    cv_splits = max(2, min(5, min_class_count))
    cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=random_state)

    rows: list[dict[str, object]] = []
    fitted_models: dict[str, object] = {}
    reports: dict[str, object] = {}

    for name, model in supervised_models(random_state).items():
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="accuracy")
        model.fit(X_train, y_train)
        predicted = model.predict(X_test)
        accuracy = accuracy_score(y_test, predicted)
        f1 = f1_score(y_test, predicted, average="macro", zero_division=0)

        rows.append(
            {
                "model": name,
                "cv_accuracy_mean": float(np.mean(cv_scores)),
                "cv_accuracy_std": float(np.std(cv_scores)),
                "test_accuracy": float(accuracy),
                "macro_f1": float(f1),
            }
        )
        fitted_models[name] = model
        reports[name] = {
            "classification_report": classification_report(y_test, predicted, zero_division=0, output_dict=True),
            "confusion_matrix": confusion_matrix(y_test, predicted, labels=sorted(y.unique())).tolist(),
        }

    results = pd.DataFrame(rows).sort_values(
        by=["cv_accuracy_mean", "test_accuracy", "macro_f1"],
        ascending=False,
    )
    best_name = str(results.iloc[0]["model"])
    return results, {"name": best_name, "model": fitted_models[best_name]}, reports


def valid_cluster_count(labels: np.ndarray) -> int:
    unique_labels = set(labels)
    unique_labels.discard(-1)
    return len(unique_labels)


def safe_cluster_scores(X_scaled: np.ndarray, y_encoded: np.ndarray, labels: np.ndarray) -> dict[str, float | None]:
    cluster_count = valid_cluster_count(labels)
    if cluster_count < 2:
        return {
            "adjusted_rand": float(adjusted_rand_score(y_encoded, labels)),
            "normalized_mutual_info": float(normalized_mutual_info_score(y_encoded, labels)),
            "silhouette": None,
            "calinski_harabasz": None,
            "davies_bouldin": None,
        }

    return {
        "adjusted_rand": float(adjusted_rand_score(y_encoded, labels)),
        "normalized_mutual_info": float(normalized_mutual_info_score(y_encoded, labels)),
        "silhouette": float(silhouette_score(X_scaled, labels)),
        "calinski_harabasz": float(calinski_harabasz_score(X_scaled, labels)),
        "davies_bouldin": float(davies_bouldin_score(X_scaled, labels)),
    }


def compare_unsupervised(X: pd.DataFrame, y: pd.Series, random_state: int) -> pd.DataFrame:
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    y_encoded = LabelEncoder().fit_transform(y)
    n_clusters = int(y.nunique())

    candidates: dict[str, np.ndarray] = {}
    candidates["kmeans"] = KMeans(n_clusters=n_clusters, n_init=20, random_state=random_state).fit_predict(X_scaled)
    candidates["agglomerative"] = AgglomerativeClustering(n_clusters=n_clusters).fit_predict(X_scaled)
    candidates["gaussian_mixture"] = GaussianMixture(n_components=n_clusters, random_state=random_state).fit_predict(X_scaled)
    candidates["dbscan"] = DBSCAN(eps=1.5, min_samples=4).fit_predict(X_scaled)

    rows = []
    for name, labels in candidates.items():
        scores = safe_cluster_scores(X_scaled, y_encoded, labels)
        rows.append(
            {
                "model": name,
                "clusters_found": valid_cluster_count(labels),
                "noise_points": int(np.sum(labels == -1)),
                **scores,
            }
        )

    return pd.DataFrame(rows).sort_values(
        by=["adjusted_rand", "normalized_mutual_info", "silhouette"],
        ascending=False,
        na_position="last",
    )


def save_comparison_plots(
    supervised_results: pd.DataFrame,
    unsupervised_results: pd.DataFrame,
    reports: dict[str, object],
    best_model_name: str,
    labels: list[str],
    output_dir: Path,
) -> dict[str, str]:
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    plot_paths: dict[str, str] = {}

    supervised_sorted = supervised_results.sort_values("test_accuracy", ascending=True)
    plt.figure(figsize=(10, 5))
    plt.barh(supervised_sorted["model"], supervised_sorted["test_accuracy"], color="#0f766e")
    plt.xlabel("Test accuracy")
    plt.xlim(0, 1)
    plt.title("Supervised Model Test Accuracy")
    plt.tight_layout()
    path = plots_dir / "supervised_accuracy.png"
    plt.savefig(path, dpi=160)
    plt.close()
    plot_paths["supervised_accuracy"] = str(path)

    f1_sorted = supervised_results.sort_values("macro_f1", ascending=True)
    plt.figure(figsize=(10, 5))
    plt.barh(f1_sorted["model"], f1_sorted["macro_f1"], color="#2563eb")
    plt.xlabel("Macro F1 score")
    plt.xlim(0, 1)
    plt.title("Supervised Model Macro F1")
    plt.tight_layout()
    path = plots_dir / "supervised_macro_f1.png"
    plt.savefig(path, dpi=160)
    plt.close()
    plot_paths["supervised_macro_f1"] = str(path)

    unsup = unsupervised_results.copy()
    unsup["adjusted_rand"] = pd.to_numeric(unsup["adjusted_rand"], errors="coerce").fillna(0)
    unsup = unsup.sort_values("adjusted_rand", ascending=True)
    plt.figure(figsize=(10, 5))
    plt.barh(unsup["model"], unsup["adjusted_rand"], color="#7c3aed")
    plt.xlabel("Adjusted Rand Index")
    plt.title("Unsupervised Clustering Quality")
    plt.tight_layout()
    path = plots_dir / "unsupervised_ari.png"
    plt.savefig(path, dpi=160)
    plt.close()
    plot_paths["unsupervised_ari"] = str(path)

    matrix = np.asarray(reports[best_model_name]["confusion_matrix"], dtype=float)
    plt.figure(figsize=(7, 6))
    plt.imshow(matrix, cmap="Blues")
    plt.title(f"Confusion Matrix: {best_model_name}")
    plt.xlabel("Predicted label")
    plt.ylabel("True label")
    plt.xticks(range(len(labels)), labels, rotation=35, ha="right")
    plt.yticks(range(len(labels)), labels)
    max_value = max(float(matrix.max()), 1.0)
    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            value = int(matrix[row, col])
            color = "white" if matrix[row, col] > max_value / 2 else "#17202a"
            plt.text(col, row, str(value), ha="center", va="center", color=color)
    plt.colorbar(label="Count")
    plt.tight_layout()
    path = plots_dir / "best_confusion_matrix.png"
    plt.savefig(path, dpi=160)
    plt.close()
    plot_paths["best_confusion_matrix"] = str(path)

    return plot_paths


def main() -> None:
    args = parse_args()
    dataset_root = PROJECT_ROOT / args.dataset
    output_dir = PROJECT_ROOT / args.output_dir
    model_path = PROJECT_ROOT / args.model_out
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    feature_table = build_feature_table(dataset_root, fs=args.fs)
    feature_table_path = output_dir / "feature_table.csv"
    feature_table.to_csv(feature_table_path, index=False)

    X = feature_table[FEATURE_NAMES]
    y = feature_table["label"]

    if y.nunique() < 2:
        raise SystemExit("Need at least two classes for model comparison.")

    supervised_results, best, reports = compare_supervised(
        X,
        y,
        test_size=args.test_size,
        random_state=args.random_state,
    )
    unsupervised_results = compare_unsupervised(X, y, random_state=args.random_state)

    supervised_path = output_dir / "supervised_results.csv"
    unsupervised_path = output_dir / "unsupervised_results.csv"
    report_path = output_dir / "supervised_reports.json"
    summary_path = output_dir / "summary.json"

    supervised_results.to_csv(supervised_path, index=False)
    unsupervised_results.to_csv(unsupervised_path, index=False)
    report_path.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    plot_paths = save_comparison_plots(
        supervised_results,
        unsupervised_results,
        reports,
        str(best["name"]),
        sorted(y.unique()),
        output_dir,
    )

    summary = {
        "dataset": str(dataset_root),
        "recordings": int(len(feature_table)),
        "classes": sorted(y.unique()),
        "best_supervised_model": best["name"],
        "best_unsupervised_model": str(unsupervised_results.iloc[0]["model"]),
        "plots": {
            name: str(Path(path).resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
            for name, path in plot_paths.items()
        },
        "notes": [
            "Use supervised classification for the final demo because labeled recordings are available.",
            "Unsupervised models are useful for discovery, sanity checks, and detecting unknown movement patterns.",
            "Retrain with real circuit data before claiming final project accuracy.",
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    bundle = {
        "model": best["model"],
        "model_name": best["name"],
        "feature_names": FEATURE_NAMES,
        "fs": args.fs,
        "labels": sorted(y.unique()),
        "trained_on": str(dataset_root),
    }
    with model_path.open("wb") as f:
        pickle.dump(bundle, f)

    print("Supervised results:")
    print(supervised_results.to_string(index=False))
    print()
    print("Unsupervised results:")
    print(unsupervised_results.to_string(index=False))
    print()
    print(f"Best supervised model saved to: {model_path}")
    print(f"Experiment outputs saved to: {output_dir}")
    print(f"Plots saved to: {output_dir / 'plots'}")


if __name__ == "__main__":
    main()
