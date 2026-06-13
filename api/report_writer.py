"""Daily Markdown/CSV report generation for Gmail scan results."""
from __future__ import annotations

from collections import Counter
import csv, io
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
