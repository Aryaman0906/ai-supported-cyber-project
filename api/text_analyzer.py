"""Real-time text/email phishing analysis helpers.

The model is trained offline by ``train/train_text_model.py`` and saved with
joblib. This module only loads the saved model and performs prediction. It does
not retrain during API requests, which keeps responses fast enough for a real-
time demo.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "text_phishing_model.joblib"


@dataclass(frozen=True)
class TextAnalysisResult:
    """Structured result returned by the text analyzer."""

    prediction: str
    confidence: float
    risk_level: str
    reasons: list[str]
    safety_note: str


class TextPhishingAnalyzer:
    """Load a saved text phishing model once and reuse it for predictions."""

    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH) -> None:
        self.model_path = model_path
        self.model: Any | None = None

    @property
    def is_loaded(self) -> bool:
        """Return True when the trained model is available in memory."""
        return self.model is not None

    def load_model(self) -> None:
        """Load the trained joblib model from disk.

        This method is called during FastAPI startup. Prediction requests should
        use the already-loaded model instead of reading from disk each time.
        """
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Text model not found at {self.model_path}. "
                "Run: python train/train_text_model.py"
            )

        self.model = joblib.load(self.model_path)

    def analyze(self, text: str) -> TextAnalysisResult:
        """Analyze user-provided email/text and return a defensive verdict."""
        if self.model is None:
            raise RuntimeError("Text phishing model is not loaded")

        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Input text cannot be empty")

        prediction = str(self.model.predict([cleaned_text])[0])
        confidence = self._get_prediction_confidence(cleaned_text, prediction)
        risk_level = self._risk_level(prediction, confidence)
        reasons = self._build_reasons(cleaned_text, prediction, confidence)

        return TextAnalysisResult(
            prediction=prediction,
            confidence=round(confidence, 4),
            risk_level=risk_level,
            reasons=reasons,
            safety_note=(
                "Defensive analysis only. This result is a learning-project signal, "
                "not a final security decision. Review suspicious messages manually."
            ),
        )

    def _get_prediction_confidence(self, text: str, prediction: str) -> float:
        """Return model confidence for the predicted class when available."""
        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba([text])[0]
            classes = [str(label) for label in self.model.classes_]
            prediction_index = classes.index(prediction)
            return float(probabilities[prediction_index])

        # Fallback for classifiers without probability support.
        return 0.50

    @staticmethod
    def _risk_level(prediction: str, confidence: float) -> str:
        """Convert prediction and confidence into a simple risk level."""
        if prediction == "phishing" and confidence >= 0.80:
            return "high"
        if prediction == "phishing":
            return "medium"
        if confidence < 0.60:
            return "low-confidence"
        return "low"

    @staticmethod
    def _build_reasons(text: str, prediction: str, confidence: float) -> list[str]:
        """Create beginner-readable reasons using safe heuristics and model output."""
        lowered_text = text.lower()
        reasons: list[str] = [
            f"The offline-trained text model predicted '{prediction}' with confidence {confidence:.2f}."
        ]

        suspicious_terms = [
            "urgent",
            "verify",
            "login",
            "password",
            "suspend",
            "locked",
            "one-time passcode",
            "banking details",
            "confidential",
            "unknown link",
        ]
        matched_terms = [term for term in suspicious_terms if term in lowered_text]
        if matched_terms:
            reasons.append(
                "The text contains common phishing-pressure or credential-related wording: "
                + ", ".join(matched_terms[:5])
                + "."
            )

        if len(text) < 25:
            reasons.append("The input is very short, so the model has limited context.")

        if prediction == "legitimate" and confidence < 0.70:
            reasons.append(
                "The message was predicted legitimate, but confidence is not very high; review manually."
            )

        if len(reasons) == 1:
            reasons.append("No simple high-risk keywords from the starter heuristic list were found.")

        return reasons
