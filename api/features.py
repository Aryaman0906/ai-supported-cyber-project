"""Feature extraction helpers for URL phishing analysis.

These features are intentionally simple and explainable for a college mini-
project. They are defensive signals only and should not be treated as proof that
any URL is safe or malicious.
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

import tldextract

# Disable live Public Suffix List fetching so feature extraction works offline.
_TLD_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=())

SUSPICIOUS_URL_KEYWORDS = [
    "login",
    "verify",
    "update",
    "password",
    "secure",
    "account",
    "banking",
    "alert",
    "confirm",
    "urgent",
    "prize",
    "claim",
    "admin",
]


def normalize_url(url: str) -> str:
    """Trim a URL and add a default scheme when the user omits one."""
    cleaned_url = url.strip()
    if not cleaned_url:
        raise ValueError("URL cannot be empty")

    if "://" not in cleaned_url:
        cleaned_url = "http://" + cleaned_url

    return cleaned_url


def has_ip_address(hostname: str) -> int:
    """Return 1 when the hostname is an IPv4 or IPv6 address, otherwise 0."""
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return 0
    return 1


def extract_url_features(url: str) -> dict[str, Any]:
    """Extract explainable numeric and boolean features from a URL."""
    normalized_url = normalize_url(url)
    parsed = urlparse(normalized_url)
    hostname = parsed.hostname or ""
    extracted = _TLD_EXTRACTOR(normalized_url)
    domain = extracted.domain or ""
    suffix = extracted.suffix or ""
    subdomain = extracted.subdomain or ""
    registered_domain = ".".join(part for part in [domain, suffix] if part)

    special_characters = re.findall(r"[^A-Za-z0-9]", normalized_url)
    suspicious_keyword_count = sum(
        1 for keyword in SUSPICIOUS_URL_KEYWORDS if keyword in normalized_url.lower()
    )

    return {
        "url_length": len(normalized_url),
        "uses_https": 1 if parsed.scheme.lower() == "https" else 0,
        "has_ip_address": has_ip_address(hostname),
        "dot_count": normalized_url.count("."),
        "hyphen_count": normalized_url.count("-"),
        "has_at_symbol": 1 if "@" in normalized_url else 0,
        "suspicious_keyword_count": suspicious_keyword_count,
        "subdomain_depth": len([part for part in subdomain.split(".") if part]),
        "domain_length": len(registered_domain),
        "special_char_count": len(special_characters),
    }


URL_FEATURE_COLUMNS = [
    "url_length",
    "uses_https",
    "has_ip_address",
    "dot_count",
    "hyphen_count",
    "has_at_symbol",
    "suspicious_keyword_count",
    "subdomain_depth",
    "domain_length",
    "special_char_count",
]
