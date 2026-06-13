"""Drive upload and local fallback for daily reports."""
from __future__ import annotations

from datetime import date as date_type
import os
from pathlib import Path
from typing import Any

from api.gmail_client import build_drive_service
from api.report_writer import generate_csv_report, generate_markdown_report, summarize_results
from api.storage import BotStorage


def write_local_report(date: str, markdown: str, csv_text: str) -> dict[str, Any]:
    folder = Path(os.getenv("REPORT_OUTPUT_DIR", "reports/generated")) / date
    folder.mkdir(parents=True, exist_ok=True)
    md_path = folder / "gmail_report.md"; csv_path = folder / "gmail_report.csv"
    md_path.write_text(markdown, encoding="utf-8"); csv_path.write_text(csv_text, encoding="utf-8")
    return {"storage": "local", "markdown_path": str(md_path), "csv_path": str(csv_path)}


def _ensure_drive_folder(service, name: str) -> str:
    query = f"mimeType='application/vnd.google-apps.folder' and name='{name}' and trashed=false"
    files = service.files().list(q=query, fields="files(id,name)").execute().get("files", [])
    if files: return files[0]["id"]
    folder = service.files().create(body={"name": name, "mimeType": "application/vnd.google-apps.folder"}, fields="id").execute()
    return folder["id"]


def _upload_text(service, folder_id: str, name: str, mime_type: str, text: str) -> dict[str, str]:
    from googleapiclient.http import MediaInMemoryUpload
    media = MediaInMemoryUpload(text.encode("utf-8"), mimetype=mime_type, resumable=False)
    file = service.files().create(body={"name": name, "parents": [folder_id]}, media_body=media, fields="id,webViewLink").execute()
    return {"id": file.get("id"), "webViewLink": file.get("webViewLink")}


def generate_daily_report(storage: BotStorage, date: str | None = None, email: str | None = None, upload_to_drive: bool = False) -> dict[str, Any]:
    date = date or date_type.today().isoformat()
    results = storage.get_scan_results_for_date(date, email=email)
    markdown = generate_markdown_report(date, results); csv_text = generate_csv_report(results)
    summary = summarize_results(results)
    output: dict[str, Any] = {"date": date, "summary": summary}
    if upload_to_drive and email:
        service = build_drive_service(storage, email)
        folder_id = _ensure_drive_folder(service, os.getenv("DRIVE_REPORT_FOLDER_NAME", "AI Cyber Reports"))
        output["drive"] = {"markdown": _upload_text(service, folder_id, f"gmail_report_{date}.md", "text/markdown", markdown), "csv": _upload_text(service, folder_id, f"gmail_report_{date}.csv", "text/csv", csv_text)}
    else:
        output["local"] = write_local_report(date, markdown, csv_text)
    storage.save_daily_report(date, output)
    return output
