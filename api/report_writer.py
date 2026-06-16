"""Daily Markdown/CSV/XLSX report generation for Gmail scan results."""
from __future__ import annotations

from collections import Counter
from io import BytesIO
import csv, io
from typing import Any


REPORT_FIELDS = ["message_id", "date", "sender_domain", "risk_level", "score", "url_domains", "reasons"]


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


def _report_row(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_id": result.get("message_id", ""),
        "date": result.get("date", ""),
        "sender_domain": result.get("sender_domain", ""),
        "risk_level": result.get("risk_level", ""),
        "score": result.get("score", ""),
        "url_domains": ";".join(result.get("url_domains", [])),
        "reasons": " | ".join(result.get("reasons", [])),
    }


def generate_csv_report(results: list[dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=REPORT_FIELDS); writer.writeheader()
    for r in results:
        writer.writerow(_report_row(r))
    return output.getvalue()


def generate_xlsx_report_bytes(date: str, results: list[dict[str, Any]]) -> bytes:
    """Generate a presentation-friendly Excel report with widths, filters, and wrapping.

    CSV stays available for raw export, but XLSX is the report to open in Drive
    or Excel when the user wants readable columns and formatting.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.table import Table, TableStyleInfo

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Gmail Report"

    title = f"AI Cyber Daily Gmail Report - {date}"
    worksheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(REPORT_FIELDS))
    title_cell = worksheet.cell(row=1, column=1, value=title)
    title_cell.font = Font(bold=True, size=14)
    title_cell.alignment = Alignment(horizontal="center")

    summary = summarize_results(results)
    summary_rows = [
        ("Total scanned", summary["total_scanned"]),
        ("High risk", summary["high_count"]),
        ("Medium risk", summary["medium_count"]),
        ("Low risk", summary["low_count"]),
        ("Unknown", summary["unknown_count"]),
    ]
    for row_index, (label, value) in enumerate(summary_rows, start=3):
        worksheet.cell(row=row_index, column=1, value=label).font = Font(bold=True)
        worksheet.cell(row=row_index, column=2, value=value)

    header_row = 10
    for col_index, field in enumerate(REPORT_FIELDS, start=1):
        cell = worksheet.cell(row=header_row, column=col_index, value=field)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.fill = PatternFill("solid", fgColor="D9EAF7")

    risk_fills = {
        "high": PatternFill("solid", fgColor="F4CCCC"),
        "medium": PatternFill("solid", fgColor="FCE5CD"),
        "low": PatternFill("solid", fgColor="D9EAD3"),
        "unknown": PatternFill("solid", fgColor="EFEFEF"),
    }

    for row_offset, result in enumerate(results, start=1):
        row_index = header_row + row_offset
        row = _report_row(result)
        for col_index, field in enumerate(REPORT_FIELDS, start=1):
            cell = worksheet.cell(row=row_index, column=col_index, value=row[field])
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        risk_level = str(row.get("risk_level", "")).lower()
        if risk_level in risk_fills:
            worksheet.cell(row=row_index, column=4).fill = risk_fills[risk_level]

    widths = {
        "A": 20,
        "B": 12,
        "C": 28,
        "D": 14,
        "E": 10,
        "F": 38,
        "G": 80,
    }
    for column, width in widths.items():
        worksheet.column_dimensions[column].width = width

    worksheet.freeze_panes = "A11"
    worksheet.auto_filter.ref = f"A{header_row}:G{max(header_row, header_row + len(results))}"

    if results:
        table_ref = f"A{header_row}:G{header_row + len(results)}"
        table = Table(displayName="GmailSecurityReport", ref=table_ref)
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True, showColumnStripes=False)
        worksheet.add_table(table)

    worksheet.sheet_view.showGridLines = False

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
