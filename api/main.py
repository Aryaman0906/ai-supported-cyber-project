"""FastAPI app for real-time defensive phishing analysis.

Phase 4 exposes POST /analyze-text and POST /analyze-url. Trained models are
loaded once when the API starts. Requests only perform prediction and do not
retrain models.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.log_analyzer import LogAnalyzer
from api.text_analyzer import TextPhishingAnalyzer
from api.url_analyzer import UrlPhishingAnalyzer

text_analyzer = TextPhishingAnalyzer()
url_analyzer = UrlPhishingAnalyzer()
log_analyzer = LogAnalyzer()
text_startup_error: str | None = None
url_startup_error: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load trained models once during application startup."""
    global text_startup_error, url_startup_error
    try:
        text_analyzer.load_model()
        text_startup_error = None
    except FileNotFoundError as error:
        # Keep the API online so /health can explain what setup step is missing.
        text_startup_error = str(error)

    try:
        url_analyzer.load_model()
        url_startup_error = None
    except FileNotFoundError as error:
        url_startup_error = str(error)

    yield


app = FastAPI(
    title="AI-Assisted Defensive Cybersecurity API",
    description="Real-time defensive analysis endpoints for sanitized emails, URLs, and logs.",
    version="0.3.0",
    lifespan=lifespan,
)

# Helpful for the later local HTML frontend. Restrict origins before real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TextAnalysisRequest(BaseModel):
    """Request body for text/email analysis."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="Sanitized email body, subject, or text snippet to analyze.",
        examples=[
            "Urgent action required: confirm your login details to avoid suspension."
        ],
    )


class TextAnalysisResponse(BaseModel):
    """Response body returned by POST /analyze-text."""

    prediction: str
    confidence: float
    risk_level: str
    reasons: list[str]
    safety_note: str


class UrlAnalysisRequest(BaseModel):
    """Request body for URL analysis."""

    url: str = Field(
        ...,
        min_length=1,
        max_length=2_048,
        description="Sanitized URL to analyze. Do not submit private or sensitive links.",
        examples=["http://verify-account.example-risk.test/confirm"],
    )
    include_external_checks: bool = Field(
        default=False,
        description=(
            "Optional. When true, the API may send the URL to configured third-party "
            "threat-intelligence providers such as VirusTotal or PhishTank."
        ),
    )


class UrlAnalysisResponse(BaseModel):
    """Response body returned by POST /analyze-url."""

    verdict: str
    score: float
    risk_level: str
    extracted_features: dict[str, Any]
    reasons: list[str]
    external_checks: dict[str, Any]
    safety_note: str


class LogAnalysisRequest(BaseModel):
    """Request body for one sanitized server log line."""

    log_line: str = Field(
        ...,
        min_length=1,
        max_length=5_000,
        description="One sanitized Apache/Nginx-style access log line to triage.",
        examples=[
            '203.0.113.50 - - [13/Jun/2026:10:01:12 +0000] "GET /.env HTTP/1.1" 404 121 "-" "Scanner-Test-Agent"'
        ],
    )


class LogAnalysisResponse(BaseModel):
    """Response body returned by POST /analyze-log-line."""

    verdict: str
    risk_score: int
    risk_level: str
    reasons: list[str]
    parsed: dict[str, Any]
    safety_note: str


@app.get("/health")
def health() -> dict[str, Any]:
    """Return API and model status for quick troubleshooting."""
    api_status = "ok" if text_analyzer.is_loaded and url_analyzer.is_loaded else "model_not_loaded"
    return {
        "status": api_status,
        "text_model_loaded": text_analyzer.is_loaded,
        "url_model_loaded": url_analyzer.is_loaded,
        "details": {
            "text_model": text_startup_error,
            "url_model": url_startup_error,
        },
    }


@app.post("/analyze-text", response_model=TextAnalysisResponse)
def analyze_text(request: TextAnalysisRequest) -> TextAnalysisResponse:
    """Analyze pasted text/email content in real time."""
    if not text_analyzer.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                text_startup_error
                or "Text model is not loaded. Run python train/train_text_model.py first."
            ),
        )

    try:
        result = text_analyzer.analyze(request.text)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return TextAnalysisResponse(
        prediction=result.prediction,
        confidence=result.confidence,
        risk_level=result.risk_level,
        reasons=result.reasons,
        safety_note=result.safety_note,
    )


@app.post("/analyze-url", response_model=UrlAnalysisResponse)
def analyze_url(request: UrlAnalysisRequest) -> UrlAnalysisResponse:
    """Analyze a URL in real time using the offline-trained URL model."""
    if not url_analyzer.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                url_startup_error
                or "URL model is not loaded. Run python train/train_url_model.py first."
            ),
        )

    try:
        result = url_analyzer.analyze(request.url, request.include_external_checks)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return UrlAnalysisResponse(
        verdict=result.verdict,
        score=result.score,
        risk_level=result.risk_level,
        extracted_features=result.extracted_features,
        reasons=result.reasons,
        external_checks=result.external_checks,
        safety_note=result.safety_note,
    )


@app.post("/analyze-log-line", response_model=LogAnalysisResponse)
def analyze_log_line(request: LogAnalysisRequest) -> LogAnalysisResponse:
    """Triage one sanitized Apache/Nginx-style log line in real time."""
    try:
        result = log_analyzer.analyze_line(request.log_line)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return LogAnalysisResponse(
        verdict=result.verdict,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        reasons=result.reasons,
        parsed=result.parsed,
        safety_note=result.safety_note,
    )
