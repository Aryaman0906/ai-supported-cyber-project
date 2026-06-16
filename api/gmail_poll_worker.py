"""Local no-billing Gmail polling worker.

Run examples:
    python -m api.gmail_poll_worker --once --limit 5
    python -m api.gmail_poll_worker --loop --interval 300 --limit 10
    python -m api.gmail_poll_worker --report-today
    python -m api.gmail_poll_worker --report-today --upload-drive

This worker uses local OAuth files in the project root:
    credentials.json  Google OAuth desktop/web client downloaded from Cloud Console
    token.json        Local OAuth token cache created after first browser login

It does not require Pub/Sub, Cloud Run, Firestore, Secret Manager, or Cloud
Scheduler. It only uses Gmail API and optionally Drive API through the existing
scope set.
"""

from __future__ import annotations

import argparse
import os
import re
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
DEFAULT_DRIVE_REPORT_FOLDER = os.getenv(
    "LOCAL_DRIVE_REPORT_FOLDER",
    "https://drive.google.com/drive/folders/1Ko8e6ldd3TasM-JQXpJO0wyYJ8S4u8EM?usp=drive_link",
)


class LocalGmailSetupError(RuntimeError):
    """Raised when local Gmail OAuth files are missing or invalid."""


def build_local_credentials(credentials_path: Path = CREDENTIALS_PATH, token_path: Path = TOKEN_PATH):
    """Build local OAuth credentials for Gmail/Drive desktop-app usage.

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

    return credentials


def build_local_gmail_service(credentials_path: Path = CREDENTIALS_PATH, token_path: Path = TOKEN_PATH):
    """Build a Gmail API service using local OAuth files."""
    from googleapiclient.discovery import build

    credentials = build_local_credentials(credentials_path, token_path)
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def build_local_drive_service(credentials_path: Path = CREDENTIALS_PATH, token_path: Path = TOKEN_PATH):
    """Build a Drive API service using the same local OAuth files."""
    from googleapiclient.discovery import build

    credentials = build_local_credentials(credentials_path, token_path)
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


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


def _format_list(values: list[Any]) -> str:
    """Format a short list for console output without exposing raw JSON."""
    clean_values = [str(value) for value in values if value]
    return ", ".join(clean_values) if clean_values else "none"


def format_scan_summary(summary: dict[str, Any]) -> str:
    """Return a human-readable local polling summary for task-log.txt.

    The returned text intentionally avoids full email bodies, OAuth tokens, and
    credentials. Skipped messages are summarized by count only so scheduled logs
    stay compact and presentation-friendly.
    """
    lines = [
        "GMAIL POLLING TASK RESULT",
        "=========================",
        f"Scanned emails : {summary.get('scanned_count', 0)}",
        f"Skipped emails : {summary.get('skipped_count', 0)}",
        f"High risk      : {summary.get('high_count', 0)}",
        f"Medium risk    : {summary.get('medium_count', 0)}",
        f"Low risk       : {summary.get('low_count', 0)}",
        f"Unknown risk   : {summary.get('unknown_count', 0)}",
    ]

    analyzed_results = [result for result in summary.get("results", []) if not result.get("skipped")]
    if not analyzed_results:
        lines.extend(["", "No newly analyzed emails in this run."])
        return "\n".join(lines)

    lines.extend(["", "Newly analyzed emails:"])
    for index, result in enumerate(analyzed_results, start=1):
        reasons = result.get("reasons") or []
        labels = result.get("labels_applied") or []
        url_domains = result.get("url_domains") or []
        lines.extend(
            [
                "",
                f"Email {index}",
                "-------",
                f"Sender        : {result.get('sender') or 'unknown'}",
                f"Subject       : {result.get('subject_preview') or '(no subject)'}",
                f"Risk level    : {result.get('risk_level') or 'unknown'}",
                f"Score         : {result.get('score', 'n/a')}",
                f"URL domains   : {_format_list(url_domains)}",
                f"Labels applied: {_format_list(labels)}",
                "Reasons       :",
            ]
        )
        if reasons:
            lines.extend(f"  - {reason}" for reason in reasons)
        else:
            lines.append("  - No reasons returned.")
    return "\n".join(lines)


def parse_drive_folder_id(folder: str | None) -> str:
    """Accept either a raw Drive folder ID or a Google Drive folder URL."""
    value = (folder or "").strip()
    if not value:
        raise LocalGmailSetupError("A Drive folder URL or folder ID is required for --upload-drive.")

    for pattern in (r"/folders/([A-Za-z0-9_-]+)", r"[?&]id=([A-Za-z0-9_-]+)"):
        match = re.search(pattern, value)
        if match:
            return match.group(1)

    if "drive.google.com" in value:
        raise LocalGmailSetupError(f"Could not extract a Drive folder ID from: {value}")

    return value


def upload_file_to_drive(service: Any, file_path: Path, folder_id: str, mime_type: str) -> dict[str, str | None]:
    """Upload one local report file into an existing Google Drive folder."""
    if not file_path.exists():
        raise LocalGmailSetupError(f"Report file not found: {file_path}")

    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=False)
    uploaded = service.files().create(
        body={"name": file_path.name, "parents": [folder_id]},
        media_body=media,
        fields="id,name,webViewLink",
    ).execute()
    return {"id": uploaded.get("id"), "name": uploaded.get("name"), "webViewLink": uploaded.get("webViewLink")}


def upload_report_to_drive(report: dict[str, Any], folder: str | None = None) -> dict[str, Any]:
    """Upload the generated Markdown and CSV reports to the configured Drive folder."""
    folder_id = parse_drive_folder_id(folder or DEFAULT_DRIVE_REPORT_FOLDER)
    drive_service = build_local_drive_service()
    markdown_path = Path(report["markdown_path"])
    csv_path = Path(report["csv_path"])
    report["drive"] = {
        "folder_id": folder_id,
        "markdown": upload_file_to_drive(drive_service, markdown_path, folder_id, "text/markdown"),
        "csv": upload_file_to_drive(drive_service, csv_path, folder_id, "text/csv"),
    }
    return report


def format_report_output(report: dict[str, Any]) -> str:
    """Return clean console output for local report generation and Drive upload."""
    lines = [
        "GMAIL POLLING REPORT GENERATED",
        "==============================",
        f"Report date : {report.get('date', 'unknown')}",
        f"Markdown    : {report.get('markdown_path', 'not generated')}",
        f"CSV         : {report.get('csv_path', 'not generated')}",
    ]

    drive = report.get("drive") or {}
    if drive:
        lines.extend(
            [
                "",
                "DRIVE UPLOAD COMPLETE",
                "=====================",
                f"Folder ID   : {drive.get('folder_id', 'unknown')}",
                f"Markdown URL: {(drive.get('markdown') or {}).get('webViewLink', 'not returned')}",
                f"CSV URL     : {(drive.get('csv') or {}).get('webViewLink', 'not returned')}",
            ]
        )

    return "\n".join(lines)


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
        print(format_scan_summary(summary), flush=True)
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
    parser.add_argument("--upload-drive", action="store_true", help="After --report-today, upload the Markdown/CSV report to Google Drive.")
    parser.add_argument(
        "--drive-folder",
        default=DEFAULT_DRIVE_REPORT_FOLDER,
        help="Drive folder URL or folder ID for --upload-drive. Defaults to LOCAL_DRIVE_REPORT_FOLDER.",
    )
    args = parser.parse_args()

    try:
        if args.report_today:
            report = generate_local_report(LocalJsonStorage(LOCAL_STORAGE_PATH))
            if args.upload_drive:
                report = upload_report_to_drive(report, args.drive_folder)
            print(format_report_output(report))
        elif args.once:
            summary = run_once(limit=args.limit, force=args.force, dry_run=args.dry_run)
            print(format_scan_summary(summary))
        elif args.loop:
            run_loop(interval=args.interval, limit=args.limit, force=args.force, dry_run=args.dry_run)
    except LocalGmailSetupError as error:
        print(f"Local Gmail setup error: {error}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
