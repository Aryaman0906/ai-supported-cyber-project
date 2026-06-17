"""Daily Markdown/CSV/XLSX report generation for Gmail scan results."""
from __future__ import annotations

from collections import Counter
import csv, html, io, zipfile
from typing import Any


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



def _worksheet_xml(rows: list[list[Any]]) -> str:
    row_xml: list[str] = []
    for row_number, row in enumerate(rows, start=1):
        cells = []
        for column_number, value in enumerate(row, start=1):
            column = chr(ord("A") + column_number - 1)
            safe_value = html.escape(str(value or ""))
            cells.append(f'<c r="{column}{row_number}" t="inlineStr"><is><t>{safe_value}</t></is></c>')
        row_xml.append(f'<row r="{row_number}">{"".join(cells)}</row>')
    return "".join(row_xml)


def generate_xlsx_report_bytes(results: list[dict[str, Any]]) -> bytes:
    """Generate a small XLSX workbook for local Gmail scan results."""
    fields = ["message_id", "date", "sender_domain", "risk_level", "score", "url_domains", "reasons"]
    rows: list[list[Any]] = [fields]
    for result in results:
        rows.append([
            result.get("message_id", ""),
            result.get("date", ""),
            result.get("sender_domain", ""),
            result.get("risk_level", ""),
            result.get("score", ""),
            ";".join(result.get("url_domains", [])),
            " | ".join(result.get("reasons", [])),
        ])

    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{_worksheet_xml(rows)}</sheetData></worksheet>'
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Gmail Report" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as workbook_zip:
        workbook_zip.writestr("[Content_Types].xml", content_types)
        workbook_zip.writestr("_rels/.rels", rels)
        workbook_zip.writestr("xl/workbook.xml", workbook)
        workbook_zip.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        workbook_zip.writestr("xl/worksheets/sheet1.xml", worksheet)
    return output.getvalue()
