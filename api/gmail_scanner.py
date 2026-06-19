"""Gmail scanning workflow for Pub/Sub notifications and manual scans."""
from __future__ import annotations

import base64, hashlib, json, os
from datetime import datetime, timezone
from typing import Any

from api.gmail_client import build_gmail_service, ensure_labels, label_names_for_risk, labels_for_risk, apply_labels, parse_gmail_message
from api.risk_engine import GmailRiskEngine
from api.storage import BotStorage, utc_now_iso


def decode_pubsub_push(envelope: dict[str, Any]) -> dict[str, Any]:
    data = envelope.get("message", {}).get("data")
    if not data:
        raise ValueError("Pub/Sub push envelope missing message.data")
    padded = data + "=" * (-len(data) % 4)
    decoded = base64.urlsafe_b64decode(padded.encode()).decode("utf-8")
    payload = json.loads(decoded)
    if "emailAddress" not in payload or "historyId" not in payload:
        raise ValueError("Gmail Pub/Sub payload must include emailAddress and historyId")
    return payload


def preview(value: str, limit: int = 140) -> str:
    return value[:limit] if os.getenv("STORE_EMAIL_PREVIEWS", "false").lower() == "true" else ""


def subject_hash(subject: str) -> str:
    return hashlib.sha256(subject.encode("utf-8")).hexdigest()


def scan_result_record(email: str, parsed, risk, labels_applied: list[str]) -> dict[str, Any]:
    date = datetime.fromtimestamp(int(parsed.internal_date or "0") / 1000, tz=timezone.utc).date().isoformat() if parsed.internal_date else datetime.now(timezone.utc).date().isoformat()
    return {
        "message_id": parsed.message_id, "thread_id": parsed.thread_id, "email": email, "date": date,
        "sender": parsed.sender, "sender_domain": parsed.sender_domain, "subject_hash": subject_hash(parsed.subject),
        "subject_preview": preview(parsed.subject), "snippet_preview": preview(parsed.snippet),
        "url_domains": parsed.url_domains, "risk_level": risk.risk_level, "score": risk.score,
        "reasons": risk.reasons, "labels_applied": labels_applied, "has_attachments": parsed.has_attachments,
        "created_at": utc_now_iso(), "updated_at": utc_now_iso(),
    }


class GmailScanner:
    def __init__(self, storage: BotStorage, risk_engine: GmailRiskEngine) -> None:
        self.storage = storage; self.risk_engine = risk_engine

    def _scan_message(self, service, email: str, message_id: str, force: bool = False) -> dict[str, Any]:
        message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        parsed = parse_gmail_message(message)
        labels = ensure_labels(service)
        if not force and labels["scanned"] in parsed.label_ids:
            return {"message_id": message_id, "skipped": True, "reason": "Already labeled AI-Cyber/Scanned"}
        combined_text = "\n".join([parsed.subject, parsed.snippet, parsed.body_text])[:10_000]
        risk = self.risk_engine.analyze(combined_text, parsed.urls)
        label_ids = labels_for_risk(risk.risk_level, labels)
        apply_labels(service, message_id, label_ids)
        record = scan_result_record(email, parsed, risk, label_names_for_risk(risk.risk_level))
        if risk.risk_level == "unknown":
            record["reasons"] = [*record["reasons"], "Unknown analysis result; review manually."]
        self.storage.save_scan_result(email, message_id, record)
        return record

    def scan_recent(self, email: str, max_results: int = 10, force: bool = False) -> dict[str, Any]:
        max_results = max(1, min(max_results, 100))
        service = build_gmail_service(self.storage, email)
        response = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=max_results).execute()
        messages = response.get("messages", [])
        results = [self._scan_message(service, email, msg["id"], force=force) for msg in messages]
        profile = service.users().getProfile(userId="me").execute()
        if profile.get("historyId"):
            self.storage.save_account(email, {"last_history_id": str(profile["historyId"])})
        return summarize_scan(results, self.storage.get_account(email))

    def process_history(self, email: str, history_id: str) -> dict[str, Any]:
        account = self.storage.get_account(email) or {}
        previous = account.get("last_history_id")
        if not previous:
            self.storage.save_account(email, {"last_history_id": str(history_id)})
            return {"status": "initialized", "message": "Stored initial historyId. Run /gmail/scan-now for initial backfill.", "history_id": str(history_id)}
        service = build_gmail_service(self.storage, email)
        try:
            history = service.users().history().list(userId="me", startHistoryId=previous, historyTypes=["messageAdded"], labelId="INBOX").execute().get("history", [])
        except Exception:
            fallback = self.scan_recent(email, max_results=10)
            self.storage.save_account(email, {"last_history_id": str(history_id)})
            return {"status": "fallback_scan", "summary": fallback, "history_id": str(history_id)}
        ids = []
        for item in history:
            for added in item.get("messagesAdded", []):
                msg = added.get("message", {})
                if "INBOX" in msg.get("labelIds", []): ids.append(msg.get("id"))
        results = [self._scan_message(service, email, mid) for mid in ids if mid]
        self.storage.save_account(email, {"last_history_id": str(history_id)})
        return {"status": "processed", "summary": summarize_scan(results, self.storage.get_account(email)), "history_id": str(history_id)}


def summarize_scan(results: list[dict[str, Any]], account: dict[str, Any] | None = None) -> dict[str, Any]:
    counts = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
    for result in results:
        if result.get("skipped"): continue
        counts[result.get("risk_level", "unknown")] = counts.get(result.get("risk_level", "unknown"), 0) + 1
    timestamps = [r.get("date") for r in results if r.get("date")]
    return {"scanned_count": sum(counts.values()), "high_count": counts["high"], "medium_count": counts["medium"], "low_count": counts["low"], "unknown_count": counts["unknown"], "newest_message_timestamp": max(timestamps) if timestamps else None, "latest_stored_history_id": (account or {}).get("last_history_id"), "results": results[:20]}
