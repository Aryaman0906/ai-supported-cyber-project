"""FastAPI app for real-time defensive phishing analysis.

Phase 4 exposes POST /analyze-text and POST /analyze-url. Trained models are
loaded once when the API starts. Requests only perform prediction and do not
retrain models.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import os
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.log_analyzer import LogAnalyzer
from api.drive_reports import generate_daily_report
from api.gmail_auth import OAuthConfigurationError, create_authorization_url, exchange_callback_for_token, gmail_oauth_config_status
from api.gmail_client import REQUIRED_LABELS, build_gmail_service
from api.gmail_scanner import GmailScanner, decode_pubsub_push
from api.risk_engine import GmailRiskEngine
from api.storage import build_storage
from api.text_analyzer import TextPhishingAnalyzer
from api.url_analyzer import UrlPhishingAnalyzer

text_analyzer = TextPhishingAnalyzer()
url_analyzer = UrlPhishingAnalyzer()
log_analyzer = LogAnalyzer()
gmail_storage = build_storage()
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
        "gmail_bot": gmail_oauth_config_status(),
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


class GmailEmailRequest(BaseModel):
    """Request body containing a Gmail account email authorized through OAuth."""

    email: str = Field(..., min_length=3, description="Authorized Gmail address to operate on.")


class GmailScanNowRequest(GmailEmailRequest):
    max_results: int = Field(default=10, ge=1, le=100)
    force: bool = Field(default=False, description="Re-scan messages even if AI-Cyber/Scanned is already applied.")


class DailyReportRequest(BaseModel):
    date: str | None = Field(default=None, description="YYYY-MM-DD date. Defaults to today.")
    email: str | None = Field(default=None, description="Authorized Gmail address for Drive upload or filtering.")
    upload_to_drive: bool = Field(default=False, description="Upload to Drive when OAuth/Drive are configured; otherwise save locally.")


class DailyMaintenanceRequest(BaseModel):
    email: str
    date: str | None = None
    scan_count: int = Field(default=10, ge=1, le=100)


def _gmail_scanner() -> GmailScanner:
    return GmailScanner(gmail_storage, GmailRiskEngine(text_analyzer, url_analyzer))


def _configured_email(request_email: str | None = None) -> str:
    email = request_email or os.getenv("GMAIL_BOT_USER_EMAIL")
    if not email:
        raise HTTPException(status_code=400, detail="Gmail email is required. Complete OAuth and pass an email, or set GMAIL_BOT_USER_EMAIL.")
    return email


@app.get("/gmail/auth/start")
def gmail_auth_start() -> dict[str, Any]:
    """Start server-side Gmail/Drive OAuth authorization."""
    try:
        return create_authorization_url(gmail_storage)
    except OAuthConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/gmail/auth/callback")
def gmail_auth_callback(request: Request) -> dict[str, Any]:
    """Handle OAuth callback and store encrypted token data."""
    try:
        return exchange_callback_for_token(gmail_storage, str(request.url), request.query_params.get("state"))
    except OAuthConfigurationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/gmail/status")
def gmail_status(email: str | None = None) -> dict[str, Any]:
    """Return Gmail bot configuration and watch status without crashing if unconfigured."""
    account = gmail_storage.get_account(email) if email else None
    return {"configured": gmail_oauth_config_status(), "email": email, "account": account, "labels": list(REQUIRED_LABELS.values())}


@app.post("/gmail/watch/start")
def gmail_watch_start(request: GmailEmailRequest) -> dict[str, Any]:
    """Register Gmail users.watch for INBOX changes."""
    topic = os.getenv("GMAIL_PUBSUB_TOPIC")
    if not topic:
        raise HTTPException(status_code=503, detail="GMAIL_PUBSUB_TOPIC is required before starting a Gmail watch")
    try:
        service = build_gmail_service(gmail_storage, request.email)
        response = service.users().watch(userId="me", body={"topicName": topic, "labelIds": ["INBOX"], "labelFilterBehavior": "INCLUDE"}).execute()
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Unable to start Gmail watch: {error}") from error
    gmail_storage.save_account(request.email, {"last_history_id": str(response.get("historyId", "")), "watch_expiration": response.get("expiration")})
    return {"status": "watch_started", "email": request.email, "history_id": response.get("historyId"), "expiration": response.get("expiration"), "note": "Gmail watches must be renewed at least every 7 days; daily renewal is recommended."}


@app.post("/gmail/watch/renew")
def gmail_watch_renew(request: GmailEmailRequest) -> dict[str, Any]:
    """Renew Gmail watch registration."""
    return gmail_watch_start(request)


@app.post("/gmail/watch/stop")
def gmail_watch_stop(request: GmailEmailRequest) -> dict[str, Any]:
    """Stop Gmail push notifications for the authorized account."""
    try:
        service = build_gmail_service(gmail_storage, request.email)
        service.users().stop(userId="me").execute()
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Unable to stop Gmail watch: {error}") from error
    gmail_storage.save_account(request.email, {"watch_expiration": None})
    return {"status": "watch_stopped", "email": request.email}


@app.post("/gmail/scan-now")
def gmail_scan_now(request: GmailScanNowRequest) -> dict[str, Any]:
    """Scan latest N inbox messages and apply AI-Cyber labels."""
    try:
        return _gmail_scanner().scan_recent(request.email, max_results=request.max_results, force=request.force)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Manual Gmail scan failed or is not configured: {error}") from error


@app.post("/gmail/pubsub/push")
def gmail_pubsub_push(envelope: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    """Handle Gmail Pub/Sub push notifications."""
    expected = os.getenv("PUBSUB_PUSH_TOKEN")
    if expected and token != expected:
        raise HTTPException(status_code=401, detail="Invalid Pub/Sub push token")
    try:
        payload = decode_pubsub_push(envelope)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    result = _gmail_scanner().process_history(payload["emailAddress"], str(payload["historyId"]))
    return {"status": "accepted", "payload": payload, "processing": result}


@app.post("/reports/generate-daily")
def reports_generate_daily(request: DailyReportRequest) -> dict[str, Any]:
    """Generate a daily Gmail security report and save locally or to Drive."""
    try:
        return generate_daily_report(gmail_storage, date=request.date, email=request.email, upload_to_drive=request.upload_to_drive)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Report generation failed: {error}") from error


@app.get("/reports/today")
def reports_today() -> dict[str, Any]:
    from datetime import date
    report = gmail_storage.get_daily_report(date.today().isoformat())
    return report or {"status": "not_found", "date": date.today().isoformat()}


@app.get("/reports/{report_date}")
def reports_by_date(report_date: str) -> dict[str, Any]:
    report = gmail_storage.get_daily_report(report_date)
    return report or {"status": "not_found", "date": report_date}


@app.post("/tasks/daily-maintenance")
def daily_maintenance(request: DailyMaintenanceRequest, x_task_secret: str | None = Header(default=None, alias="X-Task-Secret")) -> dict[str, Any]:
    """Cloud Scheduler helper: renew watch, fallback scan, and generate report."""
    expected = os.getenv("TASK_SHARED_SECRET")
    if not expected:
        raise HTTPException(status_code=503, detail="TASK_SHARED_SECRET must be set before daily maintenance can run")
    if x_task_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid task secret")
    watch = gmail_watch_renew(GmailEmailRequest(email=request.email))
    scan = _gmail_scanner().scan_recent(request.email, max_results=request.scan_count)
    report = generate_daily_report(gmail_storage, date=request.date, email=request.email, upload_to_drive=False)
    return {"watch": watch, "scan": scan, "report": report}
