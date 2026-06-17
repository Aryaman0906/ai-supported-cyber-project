"""Storage abstractions for Gmail bot account state, tokens, scans, and reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Protocol


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BotStorage(Protocol):
    def get_account(self, email: str) -> dict[str, Any] | None: ...
    def save_account(self, email: str, data: dict[str, Any]) -> None: ...
    def get_encrypted_token(self, email: str) -> str | None: ...
    def save_encrypted_token(self, email: str, encrypted_token: str) -> None: ...
    def save_scan_result(self, email: str, message_id: str, result: dict[str, Any]) -> None: ...
    def get_scan_results_for_date(self, date: str, email: str | None = None) -> list[dict[str, Any]]: ...
    def save_daily_report(self, date: str, report: dict[str, Any]) -> None: ...
    def get_daily_report(self, date: str) -> dict[str, Any] | None: ...


@dataclass
class InMemoryStorage:
    accounts: dict[str, dict[str, Any]] = field(default_factory=dict)
    encrypted_tokens: dict[str, str] = field(default_factory=dict)
    scan_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    daily_reports: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_account(self, email: str) -> dict[str, Any] | None:
        return self.accounts.get(email)

    def save_account(self, email: str, data: dict[str, Any]) -> None:
        merged = {**self.accounts.get(email, {}), **data, "email": email, "updated_at": utc_now_iso()}
        self.accounts[email] = merged

    def get_encrypted_token(self, email: str) -> str | None:
        return self.encrypted_tokens.get(email)

    def save_encrypted_token(self, email: str, encrypted_token: str) -> None:
        self.encrypted_tokens[email] = encrypted_token

    def save_scan_result(self, email: str, message_id: str, result: dict[str, Any]) -> None:
        key = f"{email}:{message_id}"
        now = utc_now_iso()
        existing = self.scan_results.get(key, {})
        self.scan_results[key] = {**existing, **result, "email": email, "message_id": message_id, "updated_at": now, "created_at": existing.get("created_at", now)}

    def get_scan_results_for_date(self, date: str, email: str | None = None) -> list[dict[str, Any]]:
        rows = []
        for result in self.scan_results.values():
            if email and result.get("email") != email:
                continue
            if str(result.get("date", "")).startswith(date):
                rows.append(result)
        return rows

    def save_daily_report(self, date: str, report: dict[str, Any]) -> None:
        self.daily_reports[date] = {**report, "date": date, "updated_at": utc_now_iso()}

    def get_daily_report(self, date: str) -> dict[str, Any] | None:
        return self.daily_reports.get(date)


class LocalJsonStorage(InMemoryStorage):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            data = {}
        super().__init__(
            accounts=data.get("accounts", {}),
            encrypted_tokens=data.get("encrypted_tokens", {}),
            scan_results=data.get("scan_results", {}),
            daily_reports=data.get("daily_reports", {}),
        )

    def _persist(self) -> None:
        self.path.write_text(json.dumps({
            "accounts": self.accounts,
            "encrypted_tokens": self.encrypted_tokens,
            "scan_results": self.scan_results,
            "daily_reports": self.daily_reports,
        }, indent=2, sort_keys=True), encoding="utf-8")

    def save_account(self, email: str, data: dict[str, Any]) -> None:
        super().save_account(email, data); self._persist()

    def save_encrypted_token(self, email: str, encrypted_token: str) -> None:
        super().save_encrypted_token(email, encrypted_token); self._persist()

    def save_scan_result(self, email: str, message_id: str, result: dict[str, Any]) -> None:
        super().save_scan_result(email, message_id, result); self._persist()

    def save_daily_report(self, date: str, report: dict[str, Any]) -> None:
        super().save_daily_report(date, report); self._persist()


class FirestoreStorage:
    def __init__(self, project_id: str | None = None) -> None:
        from google.cloud import firestore
        self.client = firestore.Client(project=project_id)

    def get_account(self, email: str) -> dict[str, Any] | None:
        doc = self.client.collection("gmail_accounts").document(email).get()
        return doc.to_dict() if doc.exists else None

    def save_account(self, email: str, data: dict[str, Any]) -> None:
        self.client.collection("gmail_accounts").document(email).set({**data, "email": email, "updated_at": utc_now_iso()}, merge=True)

    def get_encrypted_token(self, email: str) -> str | None:
        account = self.get_account(email) or {}
        return account.get("encrypted_token")

    def save_encrypted_token(self, email: str, encrypted_token: str) -> None:
        self.save_account(email, {"encrypted_token": encrypted_token})

    def save_scan_result(self, email: str, message_id: str, result: dict[str, Any]) -> None:
        now = utc_now_iso()
        ref = self.client.collection("gmail_accounts").document(email).collection("scan_results").document(message_id)
        ref.set({**result, "email": email, "message_id": message_id, "updated_at": now, "created_at": result.get("created_at", now)}, merge=True)

    def get_scan_results_for_date(self, date: str, email: str | None = None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if email:
            query = self.client.collection("gmail_accounts").document(email).collection("scan_results")
            for doc in query.where("date", ">=", date).where("date", "<", date + "~").stream():
                rows.append(doc.to_dict())
        return rows

    def save_daily_report(self, date: str, report: dict[str, Any]) -> None:
        self.client.collection("daily_reports").document(date).set({**report, "date": date, "updated_at": utc_now_iso()}, merge=True)

    def get_daily_report(self, date: str) -> dict[str, Any] | None:
        doc = self.client.collection("daily_reports").document(date).get()
        return doc.to_dict() if doc.exists else None


def build_storage() -> BotStorage:
    backend = os.getenv("STORAGE_BACKEND", "memory").lower()
    if backend == "firestore":
        return FirestoreStorage(os.getenv("GOOGLE_CLOUD_PROJECT") or None)
    if backend == "local_json":
        return LocalJsonStorage(os.getenv("LOCAL_STORAGE_PATH", ".local/gmail_bot_storage.json"))
    return InMemoryStorage()
