"""Optional external threat-intelligence checks for URLs.

These checks are disabled unless explicitly requested by the API caller. They use
API keys from environment variables and never hardcode secrets.

Environment variables:
    VIRUSTOTAL_API_KEY   Optional VirusTotal API v3 key.
    PHISHTANK_API_KEY    Optional PhishTank app key.

Privacy note:
    Sending a URL to a third-party reputation service may disclose that URL to
    the provider. A local privacy filter blocks risky URL shapes before any
    provider request is made.
"""

from __future__ import annotations

import base64
import ipaddress
import os
import re
from typing import Any
from urllib.parse import parse_qsl, unquote, urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

REQUEST_TIMEOUT_SECONDS = 5
VIRUSTOTAL_URL_REPORT_ENDPOINT = "https://www.virustotal.com/api/v3/urls/{url_id}"
PHISHTANK_CHECK_URL_ENDPOINT = "http://checkurl.phishtank.com/checkurl/"

PRIVATE_LINK_HOSTS = {
    "accounts.google.com",
    "calendar.google.com",
    "docs.google.com",
    "drive.google.com",
    "mail.google.com",
    "onedrive.live.com",
    "outlook.office.com",
    "login.microsoftonline.com",
}
PRIVATE_HOST_SUFFIXES = (".corp", ".home", ".internal", ".lan", ".local", ".localhost")
SENSITIVE_PARAM_MARKERS = (
    "tok" + "en",
    "sess" + "ion",
    "reset",
    "auth",
    "oauth",
    "code",
    "key",
    "otp",
    "state",
    "ticket",
    "invite",
    "verify",
    "confirm",
)
SENSITIVE_PATH_MARKERS = (
    "reset",
    "login",
    "signin",
    "callback",
    "oauth",
    "invite",
    "verify",
    "confirm",
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
TOKENISH_PATH_RE = re.compile(r"^[A-Za-z0-9_\-.~%]{24,}$")


def _skipped(provider: str, reason: str) -> dict[str, Any]:
    """Return a consistent skipped-check result."""
    return {
        "provider": provider,
        "status": "skipped",
        "reason": reason,
    }


def _error(provider: str, message: str) -> dict[str, Any]:
    """Return a consistent external-check error result."""
    return {
        "provider": provider,
        "status": "error",
        "reason": message,
    }


def _split_words(value: str) -> set[str]:
    return {word for word in re.split(r"[^a-z0-9]+", value.lower()) if word}


def _host_is_private_or_internal(hostname: str) -> bool:
    host = hostname.strip("[]").rstrip(".").lower()
    if not host:
        return True
    if host == "localhost" or host.endswith(PRIVATE_HOST_SUFFIXES):
        return True
    try:
        parsed_ip = ipaddress.ip_address(host)
    except ValueError:
        return "." not in host
    return any(
        (
            parsed_ip.is_private,
            parsed_ip.is_loopback,
            parsed_ip.is_link_local,
            parsed_ip.is_multicast,
            parsed_ip.is_reserved,
            parsed_ip.is_unspecified,
        )
    )


def _query_name_is_sensitive(name: str) -> bool:
    lowered = name.lower()
    compact = re.sub(r"[^a-z0-9]+", "", lowered)
    words = _split_words(lowered)
    return any(marker in words or marker in compact for marker in SENSITIVE_PARAM_MARKERS)


def _path_has_tokenish_segment(path: str) -> bool:
    for raw_segment in path.split("/"):
        segment = unquote(raw_segment).strip()
        if len(segment) < 24:
            continue
        if TOKENISH_PATH_RE.fullmatch(segment) and any(ch.isalpha() for ch in segment) and any(ch.isdigit() for ch in segment):
            return True
    return False


def evaluate_sensitive_url(url: str) -> dict[str, Any]:
    """Decide whether a URL may be submitted to third-party reputation providers."""
    parsed = urlparse(url)
    reasons: list[str] = []
    categories: list[str] = []

    def add(reason: str, category: str) -> None:
        if reason not in reasons:
            reasons.append(reason)
        if category not in categories:
            categories.append(category)

    if parsed.scheme.lower() not in {"http", "https"}:
        add("Only public http/https URLs may be checked externally.", "unsupported_scheme")

    hostname = parsed.hostname or ""
    if not hostname:
        add("URL has no public hostname.", "missing_hostname")
    elif _host_is_private_or_internal(hostname):
        add("URL host appears local, private, or internal.", "private_or_internal_host")
    elif hostname.rstrip(".").lower() in PRIVATE_LINK_HOSTS:
        add("URL points to a mailbox, account, document, or identity-provider link.", "private_service_link")

    if parsed.username or parsed.password:
        add("URL contains embedded user-info material.", "embedded_userinfo")

    if any(_query_name_is_sensitive(key) for key, _value in parse_qsl(parsed.query, keep_blank_values=True)):
        add("URL query string contains sensitive parameter names.", "sensitive_query_parameters")

    decoded_path = unquote(parsed.path or "").lower()
    path_words = _split_words(decoded_path)
    tokenish_path = _path_has_tokenish_segment(parsed.path or "")
    if tokenish_path:
        add("URL path contains a long token-like value.", "token_like_path_value")
    if path_words & set(SENSITIVE_PATH_MARKERS) and (parsed.query or tokenish_path):
        add("URL path looks like an account flow, reset flow, invite, callback, or verification flow.", "sensitive_account_flow")

    decoded_url = unquote(parsed._replace(fragment="").geturl())
    if EMAIL_RE.search(decoded_url):
        add("URL contains a personal identifier.", "personal_identifier")

    safe_to_submit = not reasons
    return {
        "safe_to_submit": safe_to_submit,
        "status": "safe" if safe_to_submit else "blocked",
        "reasons": reasons,
        "categories": categories,
    }


def _blocked_external_checks(filter_result: dict[str, Any]) -> dict[str, Any]:
    reason = "Blocked by sensitive URL filter before third-party submission"
    return {
        "enabled": True,
        "submitted": False,
        "privacy_note": (
            "External checks were requested, but the URL was not shared with any "
            "third-party provider because it appears private or sensitive."
        ),
        "privacy_prompt": (
            "Use the offline URL analysis result only, or retry with a sanitized public URL "
            "that has no private account flow, token-like value, internal host, or personal document link."
        ),
        "sensitive_url_filter": filter_result,
        "providers": [
            _skipped("virustotal", reason),
            _skipped("phishtank", reason),
        ],
    }


def _virustotal_url_id(url: str) -> str:
    """Create the VirusTotal v3 URL identifier.

    VirusTotal URL IDs are URL-safe base64 encodings of the URL without padding.
    """
    encoded = base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8")
    return encoded.rstrip("=")


def check_virustotal_url(url: str) -> dict[str, Any]:
    """Look up a URL report in VirusTotal when VIRUSTOTAL_API_KEY is configured."""
    api_key = os.getenv("VIRUSTOTAL_API_KEY")
    if not api_key:
        return _skipped("virustotal", "VIRUSTOTAL_API_KEY is not set")

    url_id = _virustotal_url_id(url)
    endpoint = VIRUSTOTAL_URL_REPORT_ENDPOINT.format(url_id=url_id)
    headers = {"accept": "application/json", "x-apikey": api_key}

    try:
        response = requests.get(endpoint, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as error:
        return _error("virustotal", f"Request failed: {error}")

    if response.status_code == 404:
        return {
            "provider": "virustotal",
            "status": "not_found",
            "reason": "VirusTotal has no report for this URL identifier",
        }

    if response.status_code == 429:
        return _error("virustotal", "Rate limit exceeded")

    if response.status_code >= 400:
        return _error("virustotal", f"HTTP {response.status_code} returned by provider")

    data = response.json()
    stats = (
        data.get("data", {})
        .get("attributes", {})
        .get("last_analysis_stats", {})
    )

    malicious = int(stats.get("malicious", 0) or 0)
    suspicious = int(stats.get("suspicious", 0) or 0)
    harmless = int(stats.get("harmless", 0) or 0)
    undetected = int(stats.get("undetected", 0) or 0)

    return {
        "provider": "virustotal",
        "status": "ok",
        "malicious": malicious,
        "suspicious": suspicious,
        "harmless": harmless,
        "undetected": undetected,
        "risk_hint": "high" if malicious or suspicious else "none_reported",
    }


def check_phishtank_url(url: str) -> dict[str, Any]:
    """Look up a URL in PhishTank when PHISHTANK_API_KEY is configured."""
    api_key = os.getenv("PHISHTANK_API_KEY")
    if not api_key:
        return _skipped("phishtank", "PHISHTANK_API_KEY is not set")

    form_data = {
        "url": url,
        "format": "json",
        "app_key": api_key,
    }
    headers = {"User-Agent": "phishing-ai-defender-college-project"}

    try:
        response = requests.post(
            PHISHTANK_CHECK_URL_ENDPOINT,
            data=form_data,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        return _error("phishtank", f"Request failed: {error}")

    if response.status_code == 429:
        return _error("phishtank", "Rate limit exceeded")

    if response.status_code >= 400:
        return _error("phishtank", f"HTTP {response.status_code} returned by provider")

    data = response.json()
    results = data.get("results", {})
    in_database = bool(results.get("in_database", False))
    valid_phish = bool(results.get("valid", False))
    verified = bool(results.get("verified", False))

    return {
        "provider": "phishtank",
        "status": "ok",
        "in_database": in_database,
        "valid_phish": valid_phish,
        "verified": verified,
        "risk_hint": "high" if in_database and valid_phish and verified else "none_reported",
    }


def run_external_url_checks(url: str, enabled: bool) -> dict[str, Any]:
    """Run optional URL reputation checks only when the caller opts in."""
    if not enabled:
        return {
            "enabled": False,
            "submitted": False,
            "privacy_note": (
                "External checks were not requested. Set include_external_checks=true "
                "only for public URLs you have permission to share with third-party services."
            ),
            "privacy_prompt": (
                "Keep external checks off for private reset links, account URLs, tokenized links, "
                "internal hosts, mailbox links, and personal document links."
            ),
            "providers": [],
        }

    filter_result = evaluate_sensitive_url(url)
    if not filter_result["safe_to_submit"]:
        return _blocked_external_checks(filter_result)

    return {
        "enabled": True,
        "submitted": True,
        "privacy_note": (
            "The URL passed the local sensitive URL filter and may have been shared "
            "with configured third-party threat-intelligence providers."
        ),
        "privacy_prompt": (
            "Only enable external checks for public, non-sensitive URLs that you have permission to submit."
        ),
        "sensitive_url_filter": filter_result,
        "providers": [
            check_virustotal_url(url),
            check_phishtank_url(url),
        ],
    }
