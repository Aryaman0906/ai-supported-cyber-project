"""FastAPI app for real-time defensive phishing analysis.

Phase 3 exposes POST /analyze-text. The trained model is loaded once when the
API starts. Requests only perform prediction and do not retrain the model.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.text_analyzer import TextPhishingAnalyzer

analyzer = TextPhishingAnalyzer()
startup_error: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the text model once during application startup."""
    global startup_error
    try:
        analyzer.load_model()
        startup_error = None
    except FileNotFoundError as error:
        # Keep the API online so /health can explain what setup step is missing.
        startup_error = str(error)
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


@app.get("/health")
def health() -> dict[str, Any]:
    """Return API and model status for quick troubleshooting."""
    return {
        "status": "ok" if analyzer.is_loaded else "model_not_loaded",
        "text_model_loaded": analyzer.is_loaded,
        "detail": startup_error,
    }


@app.post("/analyze-text", response_model=TextAnalysisResponse)
def analyze_text(request: TextAnalysisRequest) -> TextAnalysisResponse:
    """Analyze pasted text/email content in real time."""
    if not analyzer.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                startup_error
                or "Text model is not loaded. Run python train/train_text_model.py first."
            ),
        )

    try:
        result = analyzer.analyze(request.text)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return TextAnalysisResponse(
        prediction=result.prediction,
        confidence=result.confidence,
        risk_level=result.risk_level,
        reasons=result.reasons,
        safety_note=result.safety_note,
    )
