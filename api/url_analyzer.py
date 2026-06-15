"""Real-time URL phishing analysis helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from api.external_checks import run_external_url_checks
from api.features import URL_FEATURE_COLUMNS, extract_url_features, normalize_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "url_phishing_model.joblib"


@dataclass(frozen=True)
class UrlAnalysisResult:
    """Structured result returned by the URL analyzer."""

    verdict: str
    score: float
    risk_level: str
    extracted_features: dict[str, Any]
    reasons: list[str]
    external_checks: dict[str, Any]
    safety_note: str


class UrlPhishingAnalyzer:
    """Load a saved URL model once and reuse it for real-time predictions."""

    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH) -> None:
        self.model_path = model_path
        self.model: Any | None = None

    @property
    def is_loaded(self) -> bool:
        """Return True when the trained URL model is available in memory."""
        return self.model is not None

    def load_model(self) -> None:
        """Load the trained URL model from disk."""
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"URL model not found at {self.model_path}. "
                "Run: python train/train_url_model.py"
            )

        self.model = joblib.load(self.model_path)

    def analyze(self, url: str, include_external_checks: bool = False) -> UrlAnalysisResult:
        """Analyze a user-provided URL and return a defensive verdict."""
        if self.model is None:
            raise RuntimeError("URL phishing model is not loaded")

        normalized_url = normalize_url(url)
        features = extract_url_features(normalized_url)
        feature_frame = pd.DataFrame([features], columns=URL_FEATURE_COLUMNS)

        verdict = str(self.model.predict(feature_frame)[0])
        score = self._get_prediction_score(feature_frame, verdict)
        risk_level = self._risk_level(verdict, score, features)
        reasons = self._build_reasons(verdict, score, features)
        external_checks = run_external_url_checks(normalized_url, include_external_checks)

        return UrlAnalysisResult(
            verdict=verdict,
            score=round(score, 4),
            risk_level=risk_level,
            extracted_features=features,
            reasons=reasons,
            external_checks=external_checks,
            safety_note=(
                "Defensive URL analysis only. Do not visit suspicious URLs. "
                "Use this as a learning-project signal and verify manually."
            ),
        )

    def _get_prediction_score(self, feature_frame: pd.DataFrame, verdict: str) -> float:
        """Return model confidence for the predicted URL class when available."""
        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba(feature_frame)[0]
            classes = [str(label) for label in self.model.classes_]
            prediction_index = classes.index(verdict)
            return float(probabilities[prediction_index])

        return 0.50

    @staticmethod
    def _risk_level(verdict: str, score: float, features: dict[str, Any]) -> str:
        """Convert model output and high-signal features into a risk level."""
        high_signal_count = sum(
            [
                int(features["has_ip_address"] == 1),
                int(features["has_at_symbol"] == 1),
                int(features["suspicious_keyword_count"] >= 2),
                int(features["subdomain_depth"] >= 3),
            ]
        )

        if verdict == "phishing" and (score >= 0.80 or high_signal_count >= 2):
            return "high"
        if verdict == "phishing":
            return "medium"
        if score < 0.60 or high_signal_count >= 1:
            return "low-confidence"
        return "low"

    @staticmethod
    def _build_reasons(verdict: str, score: float, features: dict[str, Any]) -> list[str]:
        """Create beginner-readable reasons from model output and URL features."""
        reasons = [f"The offline-trained URL model predicted '{verdict}' with score {score:.2f}."]

        if features["uses_https"] == 0:
            reasons.append("The URL does not use HTTPS.")
        if features["has_ip_address"] == 1:
            reasons.append("The hostname is an IP address instead of a normal domain name.")
        if features["has_at_symbol"] == 1:
            reasons.append("The URL contains an '@' symbol, which can hide the real destination.")
        if features["suspicious_keyword_count"] > 0:
            reasons.append(
                "The URL contains suspicious keywords often seen in credential or urgency lures."
            )
        if features["subdomain_depth"] >= 3:
            reasons.append("The URL has many subdomain levels, which can make domains harder to read.")
        if features["hyphen_count"] >= 3:
            reasons.append("The URL contains several hyphens, a pattern sometimes seen in deceptive domains.")
        if features["special_char_count"] >= 12:
            reasons.append("The URL has many special characters, making it harder to inspect manually.")

        if len(reasons) == 1:
            reasons.append("No simple high-risk URL structure indicators were found.")

        return reasons
