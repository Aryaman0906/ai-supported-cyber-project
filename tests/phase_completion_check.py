"""Dependency-light validation checks for the mini-project phases.

Run with:
    python tests/phase_completion_check.py

The checks intentionally use only the Python standard library plus the local
rule-based log analyzer so they can run even before heavy ML/API dependencies
are installed.
"""

from __future__ import annotations

import csv
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "requirements.txt",
    "README.md",
    "data/phishing_dataset.csv",
    "data/url_dataset.csv",
    "data/sample_logs.log",
    "train/train_text_model.py",
    "train/train_url_model.py",
    "api/main.py",
    "api/text_analyzer.py",
    "api/url_analyzer.py",
    "api/log_analyzer.py",
    "api/features.py",
    "api/external_checks.py",
    "frontend/index.html",
    "monitor_logs.py",
    "report/responsible_use.md",
    "report/project_explanation.md",
    ".env.example",
]

REQUIRED_API_ENDPOINTS = [
    "/health",
    "/analyze-text",
    "/analyze-url",
    "/analyze-log-line",
]

REQUIRED_FRONTEND_ENDPOINTS = REQUIRED_API_ENDPOINTS

RESPONSIBLE_USE_SECTIONS = [
    "Defensive purpose",
    "Privacy",
    "False positives",
    "False negatives",
    "Dataset bias",
    "Adversarial evasion",
    "Human review",
    "Safe deployment",
]

PROJECT_EXPLANATION_SECTIONS = [
    "Abstract",
    "Problem statement",
    "Objectives",
    "System architecture",
    "Real-time functionality",
    "Limitations",
    "Future improvements",
]


def assert_true(condition: bool, message: str) -> None:
    """Raise a clear assertion error for a failed phase check."""
    if not condition:
        raise AssertionError(message)


def read_text(relative_path: str) -> str:
    """Read a repository file as UTF-8 text."""
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def check_required_files() -> None:
    """Verify that all phase deliverables exist."""
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    assert_true(not missing, f"Missing required files: {missing}")


def check_dataset_headers() -> None:
    """Verify the starter CSV datasets use the expected headers."""
    with (PROJECT_ROOT / "data/phishing_dataset.csv").open(newline="", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        assert_true(next(reader) == ["text", "label"], "phishing_dataset.csv must have text,label header")

    with (PROJECT_ROOT / "data/url_dataset.csv").open(newline="", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        assert_true(next(reader) == ["url", "label"], "url_dataset.csv must have url,label header")


def check_api_contract_strings() -> None:
    """Verify the documented real-time endpoints are present in api/main.py."""
    main_py = read_text("api/main.py")
    missing = [endpoint for endpoint in REQUIRED_API_ENDPOINTS if endpoint not in main_py]
    assert_true(not missing, f"api/main.py missing endpoint strings: {missing}")

    assert_true("lifespan=" in main_py, "FastAPI app should use lifespan startup loading")
    assert_true("load_model()" in main_py, "api/main.py should load saved models at startup")


def check_frontend_contract_strings() -> None:
    """Verify the frontend calls every API endpoint required for the demo."""
    html = read_text("frontend/index.html")
    missing = [endpoint for endpoint in REQUIRED_FRONTEND_ENDPOINTS if endpoint not in html]
    assert_true(not missing, f"frontend/index.html missing endpoint strings: {missing}")
    assert_true("fetch(" in html, "frontend/index.html should call FastAPI with fetch()")


def check_report_sections() -> None:
    """Verify the Phase 8 reports include required responsible-use sections."""
    responsible_use = read_text("report/responsible_use.md")
    missing_responsible = [section for section in RESPONSIBLE_USE_SECTIONS if section not in responsible_use]
    assert_true(not missing_responsible, f"responsible_use.md missing sections: {missing_responsible}")

    project_explanation = read_text("report/project_explanation.md")
    missing_explanation = [section for section in PROJECT_EXPLANATION_SECTIONS if section not in project_explanation]
    assert_true(not missing_explanation, f"project_explanation.md missing sections: {missing_explanation}")


def check_log_analyzer_smoke_test() -> None:
    """Run a real local log analyzer smoke test without external dependencies."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from api.log_analyzer import LogAnalyzer

    line = (
        '203.0.113.50 - - [13/Jun/2026:10:01:12 +0000] '
        '"GET /.env HTTP/1.1" 404 121 "-" "Scanner-Test-Agent"'
    )
    result = LogAnalyzer().analyze_line(line)
    assert_true(result.verdict == "anomalous", f"Expected anomalous verdict, got {result.verdict}")
    assert_true(result.risk_level == "high", f"Expected high risk, got {result.risk_level}")
    assert_true(result.risk_score >= 70, f"Expected score >= 70, got {result.risk_score}")


def main() -> None:
    """Run all dependency-light phase completion checks."""
    checks = [
        check_required_files,
        check_dataset_headers,
        check_api_contract_strings,
        check_frontend_contract_strings,
        check_report_sections,
        check_log_analyzer_smoke_test,
    ]

    for check in checks:
        check()
        print(f"PASS {check.__name__}")

    print("All phase completion checks passed.")


if __name__ == "__main__":
    main()
