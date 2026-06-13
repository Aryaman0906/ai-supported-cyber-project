"""Local no-billing Gmail polling worker.

Run examples:
    python -m api.gmail_poll_worker --once --limit 5
    python -m api.gmail_poll_worker --loop --interval 300 --limit 10
    python -m api.gmail_poll_worker --report-today

This worker uses local OAuth files in the project root:
    credentials.json  Google OAuth desktop/web client downloaded from Cloud Console
    token.json        Local OAuth token cache created after first browser login

It does not require Pub/Sub, Cloud Run, Firestore, Secret Manager, or Cloud
Scheduler. It only uses Gmail API and optionally Drive API through the existing
scope set.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
import time
from typing import Any

from api.gmail_auth import GMAIL_SCOPES
from api.gmail_client import (
    REQUIRED_LABELS,
    apply_labels,
    ensure_labels,
    labels_for_risk,
    parse_gmail_message,
)
from api.report_writer import generate_csv_report, generate_markdown_report
from api.risk_engine import GmailRiskEngine, RiskResult
from api.storage import LocalJsonStorage, utc_now_iso

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"
TOKEN_PATH = PROJECT_ROOT / "token.json"
LOCAL_STORAGE_PATH = PROJECT_ROOT / ".local" / "gmail_poll_storage.json"
REPORT_ROOT = PROJECT_ROOT / "reports" / "generated"


class LocalGmailSetupError(RuntimeError):
    """Raised when local Gmail OAuth files are missing or invalid."""


def build_local_gmail_service(credentials_path: Path = CREDENTIALS_PATH, token_path: Path = TOKEN_PATH):
    """Build a Gmail API service using local OAuth files.

    The first run opens a browser for user consent and writes token.json. Later
    runs reuse token.json and refresh it when possible.
    """
    if not credentials_path.exists():
        raise LocalGmailSetupError(
            "credentials.json was not found in the project root. Download an OAuth client JSON file first."
        )

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    credentials = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), GMAIL_SCOPES)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), GMAIL_SCOPES)
            credentials = flow.run_local_server(port=0)
        token_path.write_text(credentials.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def build_local_risk_engine() -> GmailRiskEngine:
    """Build the local risk engine, loading models if they exist.

    If saved models are missing, the analyzers stay unloaded and Gmail risk
    results become UNKNOWN with clear reasons instead of crashing.
    """
    from api.text_analyzer import TextPhishingAnalyzer
    from api.url_analyzer import UrlPhishingAnalyzer

    text_analyzer = TextPhishingAnalyzer()
    url_analyzer = UrlPhishingAnalyzer()
    try:
        text_analyzer.load_model()
    except FileNotFoundError:
        pass
    try:
        url_analyzer.load_model()
    except FileNotFoundError:
        pass
    return GmailRiskEngine(text_analyzer, url_analyzer)


def list_latest_inbox_message_ids(service: Any, limit: int) -> list[str]:
    """Return latest Gmail INBOX message IDs up to limit."""
    limit = max(1, min(limit, 100))
    response = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=limit).execute()
    return [message["id"] for message in response.get("messages", [])]


def fetch_full_message(service: Any, message_id: str) -> dict[str, Any]:
    """Fetch a Gmail message in full format for local analysis."""
    return service.users().messages().get(userId="me", id=message_id, format="full").execute()


def scan_message(
    service: Any,
    storage: LocalJsonStorage,
    risk_engine: GmailRiskEngine,
    message_id: str,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Scan one Gmail message, optionally applying labels and saving metadata."""
    message = fetch_full_message(service, message_id)
    parsed = parse_gmail_message(message)
    label_ids = ensure_labels(service)

    if not force and label_ids["scanned"] in parsed.label_ids:
        return {"message_id": message_id, "skipped": True, "reason": "Already labeled AI-Cyber/Scanned"}

    combined_text = "\n".join([parsed.subject, parsed.snippet, parsed.body_text])[:10_000]
    risk = risk_engine.analyze(combined_text, parsed.urls)
    applied_risk_level = "medium" if risk.risk_level == "unknown" else risk.risk_level
    labels_to_apply = labels_for_risk(applied_risk_level, label_ids)

    if not dry_run:
        apply_labels(service, message_id, labels_to_apply)

    result = scan_record(parsed, risk, [REQUIRED_LABELS["scanned"], REQUIRED_LABELS[applied_risk_level]])
    if risk.risk_level == "unknown":
        result["reasons"] = [*result["reasons"], "Unknown analysis result; review manually."]
    result["dry_run"] = dry_run
    storage.save_scan_result("local-gmail", parsed.message_id, result)
    return result


def scan_record(parsed: Any, risk: RiskResult, labels_applied: list[str]) -> dict[str, Any]:
    """Create privacy-aware local scan metadata without storing full body."""
    message_date = date.today().isoformat()
    return {
        "message_id": parsed.message_id,
        "thread_id": parsed.thread_id,
        "email": "local-gmail",
        "date": message_date,
        "sender": parsed.sender,
        "sender_domain": parsed.sender_domain,
        "subject_preview": parsed.subject[:120],
        "snippet_preview": parsed.snippet[:160],
        "url_domains": parsed.url_domains,
        "risk_level": risk.risk_level,
        "score": risk.score,
        "text_prediction": risk.text_prediction,
        "text_confidence": risk.text_confidence,
        "reasons": risk.reasons,
        "labels_applied": labels_applied,
        "has_attachments": parsed.has_attachments,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }


def scan_latest_inbox(
    service: Any,
    storage: LocalJsonStorage,
    risk_engine: GmailRiskEngine,
    limit: int,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Poll latest inbox messages and scan unprocessed messages."""
    message_ids = list_latest_inbox_message_ids(service, limit)
    results = [scan_message(service, storage, risk_engine, message_id, force=force, dry_run=dry_run) for message_id in message_ids]
    return summarize_results(results)


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize a local polling scan."""
    counts = {"high": 0, "medium": 0, "low": 0, "unknown": 0, "skipped": 0}
    for result in results:
        if result.get("skipped"):
            counts["skipped"] += 1
            continue
        risk_level = result.get("risk_level", "unknown")
        counts[risk_level] = counts.get(risk_level, 0) + 1
    return {
        "scanned_count": len([r for r in results if not r.get("skipped")]),
        "skipped_count": counts["skipped"],
        "high_count": counts["high"],
        "medium_count": counts["medium"],
        "low_count": counts["low"],
        "unknown_count": counts["unknown"],
        "results": results,
    }


def generate_local_report(storage: LocalJsonStorage, report_date: str | None = None) -> dict[str, str]:
    """Generate Markdown and CSV reports under reports/generated/YYYY-MM-DD/."""
    report_date = report_date or date.today().isoformat()
    results = storage.get_scan_results_for_date(report_date, email="local-gmail")
    output_dir = REPORT_ROOT / report_date
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "gmail_poll_report.md"
    csv_path = output_dir / "gmail_poll_report.csv"
    markdown_path.write_text(generate_markdown_report(report_date, results), encoding="utf-8")
    csv_path.write_text(generate_csv_report(results), encoding="utf-8")
    return {"date": report_date, "markdown_path": str(markdown_path), "csv_path": str(csv_path)}


def run_once(limit: int, force: bool = False, dry_run: bool = False) -> dict[str, Any]:
    """Build local dependencies and scan the latest inbox messages once."""
    service = build_local_gmail_service()
    storage = LocalJsonStorage(LOCAL_STORAGE_PATH)
    risk_engine = build_local_risk_engine()
    return scan_latest_inbox(service, storage, risk_engine, limit=limit, force=force, dry_run=dry_run)


def run_loop(interval: int, limit: int, force: bool = False, dry_run: bool = False) -> None:
    """Run local Gmail polling forever until interrupted."""
    while True:
        summary = run_once(limit=limit, force=force, dry_run=dry_run)
        print(summary)
        time.sleep(interval)


def main() -> None:
    """CLI entrypoint for local Gmail polling."""
    parser = argparse.ArgumentParser(description="Local no-billing Gmail polling security worker.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true", help="Scan the latest inbox messages once.")
    mode.add_argument("--loop", action="store_true", help="Continuously poll Gmail inbox.")
    mode.add_argument("--report-today", action="store_true", help="Generate today's local Markdown/CSV report.")
    parser.add_argument("--interval", type=int, default=300, help="Polling interval in seconds for --loop.")
    parser.add_argument("--limit", type=int, default=10, help="Latest inbox message count to scan, max 100.")
    parser.add_argument("--force", action="store_true", help="Re-scan messages already labeled AI-Cyber/Scanned.")
    parser.add_argument("--dry-run", action="store_true", help="Analyze and store metadata without applying Gmail labels.")
    args = parser.parse_args()

    try:
        if args.report_today:
            print(generate_local_report(LocalJsonStorage(LOCAL_STORAGE_PATH)))
        elif args.once:
            print(run_once(limit=args.limit, force=args.force, dry_run=args.dry_run))
        elif args.loop:
            run_loop(interval=args.interval, limit=args.limit, force=args.force, dry_run=args.dry_run)
    except LocalGmailSetupError as error:
        print(f"Local Gmail setup error: {error}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
