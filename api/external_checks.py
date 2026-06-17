"""Optional external threat-intelligence checks for URLs.

These checks are disabled unless explicitly requested by the API caller. They use
API keys from environment variables and never hardcode secrets.

Environment variables:
    VIRUSTOTAL_API_KEY   Optional VirusTotal API v3 key.
    PHISHTANK_API_KEY    Optional PhishTank app key.

Privacy note:
    Sending a URL to a third-party reputation service may disclose that URL to
    the provider. Do not submit private reset links, tokens, internal hostnames,
    or sensitive URLs.
"""

from __future__ import annotations

import base64
import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

REQUEST_TIMEOUT_SECONDS = 5
VIRUSTOTAL_URL_REPORT_ENDPOINT = "https://www.virustotal.com/api/v3/urls/{url_id}"
PHISHTANK_CHECK_URL_ENDPOINT = "http://checkurl.phishtank.com/checkurl/"


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
            "privacy_note": (
                "External checks were not requested. Set include_external_checks=true "
                "only for URLs you have permission to share with third-party services."
            ),
            "providers": [],
        }

    return {
        "enabled": True,
        "privacy_note": (
            "The submitted URL may have been shared with configured third-party "
            "threat-intelligence providers. Do not submit private or sensitive URLs."
        ),
        "providers": [
            check_virustotal_url(url),
            check_phishtank_url(url),
        ],
    }
