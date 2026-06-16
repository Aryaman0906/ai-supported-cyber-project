"""Combine text and URL analyzers into one Gmail message risk result."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SUSPICIOUS_EMAIL_KEYWORDS = ["urgent", "verify", "password", "locked", "suspend", "one-time passcode", "banking details"]

@dataclass(frozen=True)
class RiskResult:
    risk_level: str; score: float; text_prediction: str; text_confidence: float; url_results: list[dict[str, Any]]; reasons: list[str]; safety_note: str

class GmailRiskEngine:
    def __init__(self, text_analyzer: Any, url_analyzer: Any) -> None:
        self.text_analyzer = text_analyzer; self.url_analyzer = url_analyzer

    def analyze(self, text: str, urls: list[str]) -> RiskResult:
        reasons: list[str] = []
        url_results: list[dict[str, Any]] = []
        text_prediction = "unknown"; text_confidence = 0.0; score = 0.0
        if not getattr(self.text_analyzer, "is_loaded", False) or not getattr(self.url_analyzer, "is_loaded", False):
            return RiskResult("unknown", 0.0, text_prediction, text_confidence, [], ["Models are not loaded; review manually."], "Defensive Gmail analysis only. Unknown results require human review.")
        try:
            text_result = self.text_analyzer.analyze(text[:10_000] or "No text content")
            text_prediction = text_result.prediction; text_confidence = text_result.confidence
            score = max(score, float(text_confidence))
            reasons.extend(text_result.reasons[:3])
        except Exception as error:
            return RiskResult("unknown", 0.0, "unknown", 0.0, [], [f"Text analysis failed: {error}", "Unknown analysis result; review manually."], "Defensive Gmail analysis only. Unknown results require human review.")
        for url in urls[:20]:
            try:
                result = self.url_analyzer.analyze(url, include_external_checks=False)
                item = {"url": url, "verdict": result.verdict, "score": result.score, "risk_level": result.risk_level, "reasons": result.reasons}
                url_results.append(item); score = max(score, float(result.score))
            except Exception as error:
                url_results.append({"url": url, "verdict": "unknown", "score": 0.0, "risk_level": "unknown", "reasons": [str(error)]})
        lowered = text.lower()
        matched = [kw for kw in SUSPICIOUS_EMAIL_KEYWORDS if kw in lowered]
        if matched:
            reasons.append("Suspicious email keywords found: " + ", ".join(matched[:5]) + ".")
        any_high_url = any(item["risk_level"] == "high" for item in url_results)
        any_medium_url = any(item["risk_level"] in {"medium", "low-confidence"} for item in url_results)
        if (text_prediction == "phishing" and text_confidence >= 0.80) or any_high_url:
            risk = "high"
        elif text_prediction == "phishing" or any_medium_url or matched:
            risk = "medium"
        else:
            risk = "low"
        if risk == "medium" and text_prediction == "unknown":
            reasons.append("Unknown analysis result; review manually.")
        return RiskResult(risk, round(score, 4), text_prediction, text_confidence, url_results, reasons or ["No suspicious signals found."], "Defensive Gmail analysis only. Do not open links or attachments based only on this output.")
