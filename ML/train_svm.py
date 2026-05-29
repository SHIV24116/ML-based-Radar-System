"""Train an SVM classifier from labeled radar recordings.

Expected dataset layout:
    dataset/
      human/*.csv
      fan/*.csv
      background/*.csv
      pet/*.csv
"""

from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ML_DIR = Path(__file__).resolve().parent
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from feature_extraction import FEATURE_NAMES, extract_features_from_file  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train radar object/motion classifier.")
    parser.add_argument("--dataset", default="dataset", help="Dataset root folder.")
    parser.add_argument("--model-out", default="models/radar_svm.pkl", help="Model output path.")
    parser.add_argument("--features-out", default="outputs/features/features.csv", help="Feature table output.")
    parser.add_argument("--fs", type=float, default=2000.0, help="Sampling frequency in Hz.")
    parser.add_argument("--test-size", type=float, default=0.2, help="Fraction used for testing.")
    return parser.parse_args()


def build_feature_table(dataset_root: Path, fs: float) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for label_dir in sorted(p for p in dataset_root.iterdir() if p.is_dir()):
        label = label_dir.name
        for csv_path in sorted(label_dir.glob("*.csv")):
            features = extract_features_from_file(csv_path, fs=fs)
            row = dict(zip(FEATURE_NAMES, features))
            row["label"] = label
            row["file"] = str(csv_path)
            rows.append(row)

    if not rows:
        raise SystemExit(f"No CSV recordings found under {dataset_root}")

    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    dataset_root = PROJECT_ROOT / args.dataset
    model_path = PROJECT_ROOT / args.model_out
    features_path = PROJECT_ROOT / args.features_out

    table = build_feature_table(dataset_root, fs=args.fs)
    features_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(features_path, index=False)

    X = table[FEATURE_NAMES]
    y = table["label"]

    if y.nunique() < 2:
        raise SystemExit("Need at least two labels/classes before training.")

    stratify = y if table["label"].value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=args.test_size,
        random_state=42,
        stratify=stratify,
    )

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("svm", SVC(kernel="rbf", probability=True, class_weight="balanced")),
        ]
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = model.score(X_test, y_test)

    print(f"Feature table: {features_path}")
    print(f"Accuracy: {accuracy:.3f}")
    print("Confusion matrix:")
    print(confusion_matrix(y_test, predictions, labels=sorted(y.unique())))
    print("Classification report:")
    print(classification_report(y_test, predictions, zero_division=0))

    model_path.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "fs": args.fs,
        "labels": sorted(y.unique()),
    }
    with model_path.open("wb") as f:
        pickle.dump(bundle, f)
    print(f"Saved model: {model_path}")


if __name__ == "__main__":
    main()
