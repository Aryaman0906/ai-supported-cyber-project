"""Gmail/Drive API client helpers and message parsing utilities."""
from __future__ import annotations

import base64, email.utils, re
from html.parser import HTMLParser
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from api.gmail_auth import credentials_for_email
from api.storage import BotStorage

REQUIRED_LABELS = {
    "scanned": "AI-Cyber/Scanned",
    "low": "AI-Cyber/Low",
    "medium": "AI-Cyber/Medium",
    "high": "AI-Cyber/High",
}
URL_RE = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)

@dataclass(frozen=True)
class ParsedGmailMessage:
    message_id: str; thread_id: str; internal_date: str; sender: str; sender_domain: str
    subject: str; snippet: str; body_text: str; urls: list[str]; url_domains: list[str]; has_attachments: bool; label_ids: list[str]


def build_gmail_service(storage: BotStorage, email: str):
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=credentials_for_email(storage, email), cache_discovery=False)


def build_drive_service(storage: BotStorage, email: str):
    from googleapiclient.discovery import build
    return build("drive", "v3", credentials=credentials_for_email(storage, email), cache_discovery=False)


def _header(headers: list[dict[str, str]], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def decode_body_data(data: str | None) -> str:
    """Decode Gmail base64url body data safely."""
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode()).decode("utf-8", errors="replace")


class _HTMLBodyParser(HTMLParser):
    """Convert HTML email bodies to readable text while preserving href URLs."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hrefs: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if tag in {"p", "div", "br", "tr", "li", "table", "h1", "h2", "h3", "h4"}:
            self.parts.append(" ")
        if tag == "a":
            attrs_dict = {name.lower(): value for name, value in attrs if value}
            href = attrs_dict.get("href")
            if href and href.lower().startswith(("http://", "https://")) and href not in self.hrefs:
                self.hrefs.append(href)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4"}:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and data:
            self.parts.append(data)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def html_to_text(html: str) -> str:
    """Convert HTML to readable text and append visible href URLs for analysis."""
    parser = _HTMLBodyParser()
    parser.feed(html or "")
    text = _normalize_whitespace(" ".join(parser.parts))
    href_text = " ".join(parser.hrefs)
    return _normalize_whitespace(f"{text} {href_text}")


def _collect_body_parts(payload: dict[str, Any]) -> tuple[list[str], list[str], bool]:
    plain_texts: list[str] = []
    html_texts: list[str] = []
    has_attachments = False

    if payload.get("filename") and payload.get("body", {}).get("attachmentId"):
        return plain_texts, html_texts, True

    mime = (payload.get("mimeType") or "").lower()
    body_data = payload.get("body", {}).get("data")
    if mime == "text/plain":
        plain_texts.append(decode_body_data(body_data))
    elif mime == "text/html":
        html_texts.append(html_to_text(decode_body_data(body_data)))

    for part in payload.get("parts", []) or []:
        child_plain, child_html, child_has_attachments = _collect_body_parts(part)
        plain_texts.extend(child_plain)
        html_texts.extend(child_html)
        has_attachments = has_attachments or child_has_attachments

    return plain_texts, html_texts, has_attachments


def extract_email_text(payload: dict[str, Any]) -> tuple[str, bool]:
    """Extract the best readable text from a Gmail MIME payload.

    text/plain is preferred when available. If a message only contains text/html,
    the HTML is converted to readable text with href URLs preserved.
    """
    plain_texts, html_texts, has_attachments = _collect_body_parts(payload)
    selected = plain_texts if any(text.strip() for text in plain_texts) else html_texts
    return "\n".join(text for text in selected if text).strip(), has_attachments


def extract_urls(*values: str, max_urls: int = 20) -> list[str]:
    seen: list[str] = []
    for value in values:
        for match in URL_RE.findall(value or ""):
            cleaned = match.rstrip(".,;:!?]")
            if cleaned not in seen:
                seen.append(cleaned)
            if len(seen) >= max_urls:
                return seen
    return seen


def parse_gmail_message(message: dict[str, Any], max_text_chars: int = 10_000, max_urls: int = 20) -> ParsedGmailMessage:
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    sender = _header(headers, "From")
    parsed_email = email.utils.parseaddr(sender)[1]
    sender_domain = parsed_email.split("@")[-1].lower() if "@" in parsed_email else ""
    subject = _header(headers, "Subject")
    snippet = message.get("snippet", "")
    body_text, has_attachments = extract_email_text(payload)
    body_text = body_text[:max_text_chars]
    urls = extract_urls(subject, snippet, body_text, max_urls=max_urls)
    domains = sorted({urlparse(url).hostname or "" for url in urls if urlparse(url).hostname})
    return ParsedGmailMessage(
        message_id=message.get("id", ""), thread_id=message.get("threadId", ""), internal_date=message.get("internalDate", ""),
        sender=sender, sender_domain=sender_domain, subject=subject, snippet=snippet, body_text=body_text,
        urls=urls, url_domains=domains, has_attachments=has_attachments, label_ids=message.get("labelIds", []),
    )


def ensure_labels(service) -> dict[str, str]:
    existing = service.users().labels().list(userId="me").execute().get("labels", [])
    name_to_id = {label["name"]: label["id"] for label in existing}
    for name in REQUIRED_LABELS.values():
        if name not in name_to_id:
            created = service.users().labels().create(userId="me", body={"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}).execute()
            name_to_id[name] = created["id"]
    return {key: name_to_id[name] for key, name in REQUIRED_LABELS.items()}


def labels_for_risk(risk_level: str, label_ids: dict[str, str]) -> list[str]:
    mapped = "medium" if risk_level in {"unknown", "medium"} else "high" if risk_level == "high" else "low"
    return [label_ids["scanned"], label_ids[mapped]]


def apply_labels(service, message_id: str, label_ids: list[str]) -> None:
    service.users().messages().modify(userId="me", id=message_id, body={"addLabelIds": label_ids, "removeLabelIds": []}).execute()
