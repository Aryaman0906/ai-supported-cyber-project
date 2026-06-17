from __future__ import annotations

import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.build_datasets import build_datasets, clean_text_frame, clean_url_frame


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def create_temp_data_dir(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    write_csv(
        data_dir / "phishing_dataset.csv",
        ["text", "label"],
        [
            {"text": " Hello team ", "label": "Legitimate"},
            {"text": "Share your password now", "label": "PHISHING"},
            {"text": "Share your password now", "label": "phishing"},
            {"text": "Bad label row", "label": "spam"},
        ],
    )
    write_csv(
        data_dir / "url_dataset.csv",
        ["url", "label"],
        [
            {"url": "https://example.com/help", "label": "LEGITIMATE"},
            {"url": "http://verify.example-risk.test/login", "label": "phishing"},
            {"url": "http://verify.example-risk.test/login", "label": "phishing"},
            {"url": "https://invalid.example", "label": "unknown"},
        ],
    )
    write_csv(
        data_dir / "raw" / "synthetic_text_examples.csv",
        ["text", "label", "source", "category", "notes"],
        [
            {"text": "Portal closes Friday", "label": "legitimate", "source": "synthetic", "category": "student_portal", "notes": "safe"},
            {"text": "Send your OTP", "label": "phishing", "source": "synthetic", "category": "otp_theft", "notes": "safe"},
        ],
    )
    write_csv(
        data_dir / "raw" / "synthetic_url_examples.csv",
        ["url", "label", "source", "category", "date_added"],
        [
            {"url": "https://example.org/notice", "label": "legitimate", "source": "synthetic", "category": "workplace_notice", "date_added": "2026-06-17"},
            {"url": "http://otp.example-risk.test/code", "label": "phishing", "source": "synthetic", "category": "otp_theft", "date_added": "2026-06-17"},
        ],
    )
    return data_dir


def test_duplicate_text_rows_and_invalid_labels_are_removed():
    rows = clean_text_frame([
        {"text": " Same text ", "label": "PHISHING"},
        {"text": "Same text", "label": "phishing"},
        {"text": "Valid notice", "label": "legitimate"},
        {"text": "Invalid", "label": "spam"},
    ])
    assert [row["text"] for row in rows] == ["Same text", "Valid notice"]
    assert {row["label"] for row in rows} == {"legitimate", "phishing"}


def test_duplicate_url_rows_and_invalid_labels_are_removed():
    rows = clean_url_frame([
        {"url": " http://example-risk.test/login ", "label": "phishing"},
        {"url": "http://example-risk.test/login", "label": "PHISHING"},
        {"url": "https://example.com", "label": "legitimate"},
        {"url": "https://example.invalid", "label": "bad"},
    ])
    assert [row["url"] for row in rows] == ["http://example-risk.test/login", "https://example.com"]
    assert {row["label"] for row in rows} == {"legitimate", "phishing"}


def test_builder_exports_expected_columns_and_both_classes(tmp_path):
    data_dir = create_temp_data_dir(tmp_path)
    build_datasets(data_dir)

    text_final = read_csv(data_dir / "phishing_dataset.csv")
    url_final = read_csv(data_dir / "url_dataset.csv")
    text_master = read_csv(data_dir / "processed" / "phishing_dataset_master.csv")
    url_master = read_csv(data_dir / "processed" / "url_dataset_master.csv")

    assert list(text_final[0].keys()) == ["text", "label"]
    assert list(url_final[0].keys()) == ["url", "label"]
    assert list(text_master[0].keys()) == ["text", "label", "source", "category", "notes"]
    assert list(url_master[0].keys()) == ["url", "label", "source", "category", "date_added"]
    assert {row["label"] for row in text_final} == {"legitimate", "phishing"}
    assert {row["label"] for row in url_final} == {"legitimate", "phishing"}
    assert len({row["text"] for row in text_final}) == len(text_final)
    assert len({row["url"] for row in url_final}) == len(url_final)
