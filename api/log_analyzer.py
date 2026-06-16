"""Defensive log triage helpers for sanitized Apache/Nginx-style logs.

The analyzer is local-only and rule-based for Phase 6. It does not attack,
scan, exploit, or connect to any external system. It simply parses sample log
lines and highlights patterns that may deserve human review.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import re
from typing import Any

LOG_PATTERN = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] '
    r'"(?P<method>[A-Z]+) (?P<path>\S+) (?P<protocol>[^"]+)" '
    r'(?P<status>\d{3}) (?P<size>\S+) "(?P<referrer>[^"]*)" "(?P<user_agent>[^"]*)"'
)

SUSPICIOUS_PATH_KEYWORDS = [
    "/admin",
    "/wp-login",
    "/.env",
    "/backup",
    "/config",
    "/phpmyadmin",
    "/server-status",
]

SCANNING_EXTENSIONS = [".zip", ".bak", ".sql", ".env", ".old"]


@dataclass(frozen=True)
class ParsedLogLine:
    """Structured representation of one parsed web server log line."""

    ip: str
    timestamp: str
    method: str
    path: str
    protocol: str
    status: int
    size: str
    referrer: str
    user_agent: str


@dataclass(frozen=True)
class LogAnalysisResult:
    """Structured result returned by log triage."""

    verdict: str
    risk_score: int
    risk_level: str
    reasons: list[str]
    parsed: dict[str, Any]
    safety_note: str


@dataclass
class LogTriageState:
    """Small in-memory counters for repeated suspicious behavior."""

    max_events_per_ip: int = 50
    ip_status_history: dict[str, deque[int]] = field(default_factory=lambda: defaultdict(deque))
    ip_path_history: dict[str, deque[str]] = field(default_factory=lambda: defaultdict(deque))

    def record(self, parsed: ParsedLogLine) -> None:
        """Record one parsed event for simple frequency-based checks."""
        status_history = self.ip_status_history[parsed.ip]
        path_history = self.ip_path_history[parsed.ip]

        status_history.append(parsed.status)
        path_history.append(parsed.path)

        while len(status_history) > self.max_events_per_ip:
            status_history.popleft()
        while len(path_history) > self.max_events_per_ip:
            path_history.popleft()

    def repeated_404_count(self, ip: str) -> int:
        """Return how many recent requests from an IP were 404s."""
        return sum(1 for status in self.ip_status_history[ip] if status == 404)

    def recent_request_count(self, ip: str) -> int:
        """Return how many recent requests are tracked for an IP."""
        return len(self.ip_path_history[ip])

    def unique_recent_path_count(self, ip: str) -> int:
        """Return how many unique paths an IP recently requested."""
        return len(set(self.ip_path_history[ip]))


class LogAnalyzer:
    """Parse and triage sanitized server log lines."""

    def __init__(self) -> None:
        self.state = LogTriageState()

    def parse_line(self, line: str) -> ParsedLogLine:
        """Parse one Apache/Nginx-style access log line."""
        cleaned_line = line.strip()
        if not cleaned_line:
            raise ValueError("Log line cannot be empty")

        match = LOG_PATTERN.match(cleaned_line)
        if not match:
            raise ValueError("Log line does not match the expected Apache/Nginx-style format")

        parts = match.groupdict()
        return ParsedLogLine(
            ip=parts["ip"],
            timestamp=parts["timestamp"],
            method=parts["method"],
            path=parts["path"],
            protocol=parts["protocol"],
            status=int(parts["status"]),
            size=parts["size"],
            referrer=parts["referrer"],
            user_agent=parts["user_agent"],
        )

    def analyze_line(self, line: str) -> LogAnalysisResult:
        """Analyze one log line and update local triage counters."""
        parsed = self.parse_line(line)
        self.state.record(parsed)

        risk_score = 0
        reasons: list[str] = []
        path_lower = parsed.path.lower()
        user_agent_lower = parsed.user_agent.lower()

        matched_keywords = [keyword for keyword in SUSPICIOUS_PATH_KEYWORDS if keyword in path_lower]
        if matched_keywords:
            risk_score += 35
            reasons.append(
                "Request targeted sensitive or commonly probed path(s): "
                + ", ".join(matched_keywords)
                + "."
            )

        if parsed.status == 404:
            risk_score += 10
            reasons.append("Request returned 404, which can indicate probing when repeated.")
        elif parsed.status in {401, 403}:
            risk_score += 15
            reasons.append("Request returned an authentication/authorization failure status.")

        if any(path_lower.endswith(extension) for extension in SCANNING_EXTENSIONS):
            risk_score += 20
            reasons.append("Requested path ends with a file extension often targeted during scanning.")

        recent_404s = self.state.repeated_404_count(parsed.ip)
        if recent_404s >= 3:
            risk_score += 25
            reasons.append(f"IP has {recent_404s} recent 404 responses in this local analyzer session.")

        recent_requests = self.state.recent_request_count(parsed.ip)
        unique_paths = self.state.unique_recent_path_count(parsed.ip)
        if recent_requests >= 5 and unique_paths >= 5:
            risk_score += 20
            reasons.append(
                "IP has requested many different paths recently, which can look like scanning."
            )

        if "scanner" in user_agent_lower or "bot" in user_agent_lower:
            risk_score += 10
            reasons.append("User-Agent contains scanner/bot-like wording.")

        risk_score = min(risk_score, 100)
        risk_level = self._risk_level(risk_score)
        verdict = "anomalous" if risk_score >= 60 else "suspicious" if risk_score >= 30 else "normal"

        if not reasons:
            reasons.append("No simple suspicious log patterns were detected for this line.")

        return LogAnalysisResult(
            verdict=verdict,
            risk_score=risk_score,
            risk_level=risk_level,
            reasons=reasons,
            parsed={
                "ip": parsed.ip,
                "timestamp": parsed.timestamp,
                "method": parsed.method,
                "path": parsed.path,
                "protocol": parsed.protocol,
                "status": parsed.status,
                "size": parsed.size,
                "referrer": parsed.referrer,
                "user_agent": parsed.user_agent,
            },
            safety_note=(
                "Defensive local log triage only. Use sanitized logs and confirm alerts "
                "with human review before taking action."
            ),
        )

    @staticmethod
    def _risk_level(risk_score: int) -> str:
        """Convert numeric score into a simple risk level."""
        if risk_score >= 70:
            return "high"
        if risk_score >= 30:
            return "medium"
        return "low"
