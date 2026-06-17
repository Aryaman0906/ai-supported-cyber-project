"""Train a simple defensive URL phishing classifier.

Training is offline. The FastAPI app added in Phase 4 loads the saved model for
real-time URL analysis and never retrains during prediction requests.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from api.features import URL_FEATURE_COLUMNS, extract_url_features

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "url_dataset.csv"
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODEL_DIR / "url_phishing_model.joblib"


def load_dataset(path: Path) -> pd.DataFrame:
    """Load and validate URL training data."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    dataset = pd.read_csv(path)
    required_columns = {"url", "label"}
    missing_columns = required_columns - set(dataset.columns)
    if missing_columns:
        raise ValueError(f"Dataset is missing columns: {sorted(missing_columns)}")

    dataset = dataset.dropna(subset=["url", "label"]).copy()
    dataset["url"] = dataset["url"].astype(str).str.strip()
    dataset["label"] = dataset["label"].astype(str).str.strip().str.lower()
    dataset = dataset[dataset["url"] != ""]

    allowed_labels = {"legitimate", "phishing"}
    unexpected_labels = set(dataset["label"]) - allowed_labels
    if unexpected_labels:
        raise ValueError(f"Unexpected labels found: {sorted(unexpected_labels)}")

    if dataset["label"].nunique() < 2:
        raise ValueError("Training requires at least two classes: legitimate and phishing")

    return dataset


def build_feature_table(urls: pd.Series) -> pd.DataFrame:
    """Convert raw URLs into a numeric feature table."""
    feature_rows = [extract_url_features(url) for url in urls]
    return pd.DataFrame(feature_rows, columns=URL_FEATURE_COLUMNS)


def build_model() -> Pipeline:
    """Create a simple Random Forest URL classifier pipeline."""
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=100,
                    random_state=42,
                    class_weight="balanced",
                ),
            ),
        ]
    )


def print_evaluation(y_true: pd.Series, y_pred: list[str]) -> None:
    """Print model metrics for defensive review."""
    accuracy = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="weighted",
        zero_division=0,
    )

    print("\nURL model evaluation metrics")
    print("============================")
    print(f"Accuracy : {accuracy:.3f}")
    print(f"Precision: {precision:.3f}")
    print(f"Recall   : {recall:.3f}")
    print(f"F1-score : {f1:.3f}")

    print("\nClassification report")
    print("=====================")
    print(classification_report(y_true, y_pred, zero_division=0))

    print("Confusion matrix")
    print("================")
    print("Labels: ['legitimate', 'phishing']")
    print(confusion_matrix(y_true, y_pred, labels=["legitimate", "phishing"]))


def main() -> None:
    """Train, evaluate, and save the URL phishing model."""
    dataset = load_dataset(DATA_PATH)
    features = build_feature_table(dataset["url"])
    labels = dataset["label"]

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=0.30,
        random_state=42,
        stratify=labels,
    )

    model = build_model()
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    print_evaluation(y_test, predictions)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"\nSaved trained URL model to: {MODEL_PATH}")


if __name__ == "__main__":
    main()
