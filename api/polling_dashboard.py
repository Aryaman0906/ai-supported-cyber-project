"""Helpers for the local Gmail polling dashboard endpoints.

This module intentionally uses only local files and the local polling worker. It
never reads or returns credentials.json/token.json contents.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api import gmail_poll_worker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"
TOKEN_PATH = PROJECT_ROOT / "token.json"
REPORTS_DIR = PROJECT_ROOT / "reports" / "generated"
TASK_LOG_PATH = REPORTS_DIR / "task-log.txt"


def modified_time(path: Path) -> str | None:
    """Return an ISO modified timestamp for a path, if it exists."""
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def list_report_folders(reports_dir: Path = REPORTS_DIR) -> list[dict[str, Any]]:
    """List generated report folders, ignoring accidental non-date folders."""
    if not reports_dir.exists():
        return []

    folders: list[dict[str, Any]] = []
    for folder in sorted(reports_dir.iterdir(), reverse=True):
        if not folder.is_dir():
            continue
        # Ignore accidental folders like the old "string" folder; report dates are YYYY-MM-DD.
        if len(folder.name) != 10 or folder.name.count("-") != 2:
            continue
        markdown_files = sorted(str(path) for path in folder.glob("*.md"))
        csv_files = sorted(str(path) for path in folder.glob("*.csv"))
        folders.append(
            {
                "date": folder.name,
                "path": str(folder),
                "modified_time": modified_time(folder),
                "markdown_files": markdown_files,
                "csv_files": csv_files,
            }
        )
    return folders


def polling_status() -> dict[str, Any]:
    """Return local Gmail polling dashboard status without exposing secrets."""
    reports = list_report_folders(REPORTS_DIR)
    latest_report = reports[0] if reports else None
    return {
        "bot_mode": "local polling",
        "automation_note": "Windows Task Scheduler expected for automation; Cloud Run/PubSub are not required.",
        "credentials_json_exists": CREDENTIALS_PATH.exists(),
        "token_json_exists": TOKEN_PATH.exists(),
        "reports_generated_exists": REPORTS_DIR.exists(),
        "latest_task_log_modified_time": modified_time(TASK_LOG_PATH),
        "latest_report_date": latest_report["date"] if latest_report else None,
        "latest_report_files": latest_report if latest_report else None,
        "report_count": len(reports),
    }


def latest_log(max_lines: int = 100, log_path: Path = TASK_LOG_PATH) -> dict[str, Any]:
    """Return the last max_lines from reports/generated/task-log.txt."""
    if not log_path.exists():
        return {"exists": False, "path": str(log_path), "lines": []}
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-max_lines:]
    return {"exists": True, "path": str(log_path), "modified_time": modified_time(log_path), "lines": lines}


def reports_index() -> dict[str, Any]:
    """Return all generated report folders and files."""
    return {"reports_dir": str(REPORTS_DIR), "reports": list_report_folders(REPORTS_DIR)}


def run_scan_now(limit: int = 20, dry_run: bool = False) -> dict[str, Any]:
    """Run the local polling worker once, matching python -m api.gmail_poll_worker --once."""
    return gmail_poll_worker.run_once(limit=limit, dry_run=dry_run)


def generate_today_report() -> dict[str, str]:
    """Generate today's local Gmail polling report."""
    storage = gmail_poll_worker.LocalJsonStorage(gmail_poll_worker.LOCAL_STORAGE_PATH)
    return gmail_poll_worker.generate_local_report(storage)
