"""Train a simple defensive text/email phishing classifier.

This script is intentionally separate from the FastAPI application that will be
added in Phase 3. Training is an offline step: run this script when the dataset
changes, save the model once, and let the API load the saved model for real-time
predictions later.

Dataset format:
    data/phishing_dataset.csv with columns: text,label

Labels supported by the starter dataset:
    legitimate
    phishing
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "phishing_dataset.csv"
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODEL_DIR / "text_phishing_model.joblib"


def load_dataset(path: Path) -> pd.DataFrame:
    """Load and validate the CSV dataset used for training."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    dataset = pd.read_csv(path)
    required_columns = {"text", "label"}
    missing_columns = required_columns - set(dataset.columns)
    if missing_columns:
        raise ValueError(f"Dataset is missing columns: {sorted(missing_columns)}")

    # Keep the example beginner-friendly: remove blank text rows and normalize labels.
    dataset = dataset.dropna(subset=["text", "label"]).copy()
    dataset["text"] = dataset["text"].astype(str).str.strip()
    dataset["label"] = dataset["label"].astype(str).str.strip().str.lower()
    dataset = dataset[dataset["text"] != ""]

    allowed_labels = {"legitimate", "phishing"}
    unexpected_labels = set(dataset["label"]) - allowed_labels
    if unexpected_labels:
        raise ValueError(f"Unexpected labels found: {sorted(unexpected_labels)}")

    if dataset["label"].nunique() < 2:
        raise ValueError("Training requires at least two classes: legitimate and phishing")

    return dataset


def build_model() -> Pipeline:
    """Create a TF-IDF + Logistic Regression text classification pipeline."""
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    stop_words="english",
                    ngram_range=(1, 2),
                    min_df=1,
                ),
            ),
            (
                "classifier",
                LogisticRegression(max_iter=1000, class_weight="balanced"),
            ),
        ]
    )


def print_evaluation(y_true: pd.Series, y_pred: list[str]) -> None:
    """Print metrics that are more informative than accuracy alone."""
    accuracy = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="weighted",
        zero_division=0,
    )

    print("\nEvaluation metrics")
    print("==================")
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
    """Train, evaluate, and save the starter text phishing model."""
    dataset = load_dataset(DATA_PATH)

    x_train, x_test, y_train, y_test = train_test_split(
        dataset["text"],
        dataset["label"],
        test_size=0.30,
        random_state=42,
        stratify=dataset["label"],
    )

    model = build_model()
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    print_evaluation(y_test, predictions)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"\nSaved trained model to: {MODEL_PATH}")


if __name__ == "__main__":
    main()
