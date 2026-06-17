"""Daily Markdown/CSV/XLSX report generation for Gmail scan results."""
from __future__ import annotations

from collections import Counter
import csv
import io
from typing import Any

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(result.get("risk_level", "unknown") for result in results)
    suspicious = [r for r in results if r.get("risk_level") in {"high", "medium", "unknown"}]
    return {
        "total_scanned": len(results), "high_count": counts["high"], "medium_count": counts["medium"], "low_count": counts["low"], "unknown_count": counts["unknown"],
        "top_sender_domains": Counter(r.get("sender_domain", "") for r in suspicious if r.get("sender_domain")).most_common(10),
        "top_url_domains": Counter(domain for r in suspicious for domain in r.get("url_domains", [])).most_common(10),
        "high_risk_messages": [r for r in results if r.get("risk_level") == "high"][:25],
    }


def generate_markdown_report(date: str, results: list[dict[str, Any]]) -> str:
    summary = summarize_results(results)
    lines = [f"# AI Cyber Daily Gmail Report - {date}", "", "## Summary", "", f"- Total scanned: {summary['total_scanned']}", f"- High risk: {summary['high_count']}", f"- Medium risk: {summary['medium_count']}", f"- Low risk: {summary['low_count']}", f"- Unknown: {summary['unknown_count']}", "", "## Top suspicious sender domains"]
    lines += [f"- {d}: {c}" for d, c in summary["top_sender_domains"]] or ["- None"]
    lines += ["", "## Top suspicious URL domains"]
    lines += [f"- {d}: {c}" for d, c in summary["top_url_domains"]] or ["- None"]
    lines += ["", "## High risk message summaries"]
    for r in summary["high_risk_messages"]:
        lines.append(f"- Message `{r.get('message_id')}` from `{r.get('sender_domain')}` score={r.get('score')} reasons={'; '.join(r.get('reasons', [])[:3])}")
    if not summary["high_risk_messages"]: lines.append("- None")
    lines += ["", "## Safety note", "This report is an assistive defensive signal only. Do not open suspicious links or attachments. Human review is required."]
    return "\n".join(lines) + "\n"


def generate_csv_report(results: list[dict[str, Any]]) -> str:
    output = io.StringIO()
    fields = ["message_id", "date", "sender_domain", "risk_level", "score", "url_domains", "reasons"]
    writer = csv.DictWriter(output, fieldnames=fields); writer.writeheader()
    for r in results:
        writer.writerow({"message_id": r.get("message_id", ""), "date": r.get("date", ""), "sender_domain": r.get("sender_domain", ""), "risk_level": r.get("risk_level", ""), "score": r.get("score", ""), "url_domains": ";".join(r.get("url_domains", [])), "reasons": " | ".join(r.get("reasons", []))})
    return output.getvalue()


def _first_present(result: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = result.get(key)
        if value not in (None, ""):
            return value
    return ""


def _clean_excel_value(value: Any) -> str:
    """Convert a scan value into safe, readable Excel cell text."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        value = "; ".join(str(item) for item in value if item is not None)
    text = str(value)
    text = ILLEGAL_CHARACTERS_RE.sub("", text)
    return " ".join(text.replace("\r", " ").replace("\n", " ").split())


def _risk_fill(risk_value: Any) -> PatternFill:
    risk = str(risk_value or "").strip().lower()
    if risk in {"high", "phishing", "dangerous", "malicious"}:
        return PatternFill("solid", fgColor="FCE4E4")
    if risk in {"medium", "suspicious", "warning"}:
        return PatternFill("solid", fgColor="FFF2CC")
    if risk in {"low", "safe", "legitimate", "clean"}:
        return PatternFill("solid", fgColor="E2F0D9")
    if risk in {"unknown", "n/a", "na", ""}:
        return PatternFill("solid", fgColor="E7E6E6")
    return PatternFill("solid", fgColor="E7E6E6")


def _xlsx_row(result: dict[str, Any]) -> list[str]:
    return [
        _clean_excel_value(_first_present(result, ("message_id", "id", "gmail_message_id"))),
        _clean_excel_value(_first_present(result, ("created_at", "date", "scanned_at", "scan_time", "timestamp"))),
        _clean_excel_value(_first_present(result, ("sender", "from", "from_email"))),
        _clean_excel_value(_first_present(result, ("sender_domain",))),
        _clean_excel_value(_first_present(result, ("subject_preview", "subject", "email_subject"))),
        _clean_excel_value(_first_present(result, ("risk_level", "risk", "prediction"))),
        _clean_excel_value(_first_present(result, ("score", "risk_score", "confidence"))),
        _clean_excel_value(_first_present(result, ("labels_applied", "label", "gmail_label", "applied_label"))),
        _clean_excel_value(_first_present(result, ("reasons", "reason", "explanation", "summary", "details"))),
    ]


def generate_xlsx_report_bytes(results: list[dict[str, Any]]) -> bytes:
    """Generate a formatted XLSX workbook for local Gmail scan results."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Gmail Report"

    headers = [
        "Message ID",
        "Scanned At",
        "Sender",
        "Sender Domain",
        "Subject",
        "Risk Level",
        "Score",
        "Gmail Label",
        "Reason",
    ]
    worksheet.append(headers)
    for result in results:
        worksheet.append(_xlsx_row(result))

    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    thin_side = Side(style="thin", color="D9E2F3")
    border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    wrap_alignment = Alignment(wrap_text=True, vertical="top")

    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row, max_col=len(headers)):
        fill = _risk_fill(row[5].value)
        for cell in row:
            cell.fill = fill
            cell.alignment = wrap_alignment
            cell.border = border

    for column_index, width in enumerate([22, 22, 32, 24, 42, 16, 12, 28, 64], start=1):
        worksheet.column_dimensions[get_column_letter(column_index)].width = width
    worksheet.row_dimensions[1].height = 24
    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    last_row = max(worksheet.max_row, 1)
    table_ref = f"A1:{get_column_letter(len(headers))}{last_row}"
    table = Table(displayName="GmailPollingReport", ref=table_ref)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=False,
        showColumnStripes=False,
    )
    worksheet.add_table(table)

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()
