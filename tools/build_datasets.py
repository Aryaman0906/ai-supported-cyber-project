"""Build safe training datasets from synthetic/raw starter files.

This script intentionally uses local CSV files only. It does not fetch public
phishing feeds, scrape inboxes, or include private data.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from pathlib import Path
from typing import Iterable

ALLOWED_LABELS = {"legitimate", "phishing"}
TEXT_FINAL_COLUMNS = ["text", "label"]
TEXT_MASTER_COLUMNS = ["text", "label", "source", "category", "notes"]
URL_FINAL_COLUMNS = ["url", "label"]
URL_MASTER_COLUMNS = ["url", "label", "source", "category", "date_added"]

Row = dict[str, str]


def normalize_whitespace(value: object) -> str:
    """Return a safe one-line string with collapsed whitespace."""
    return " ".join(str(value or "").split())


def _validate_columns(columns: Iterable[str], required_columns: list[str], path: Path) -> None:
    missing = [column for column in required_columns if column not in columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")


def _read_csv(path: Path, required_columns: list[str]) -> list[Row]:
    if not path.exists():
        raise FileNotFoundError(f"Required dataset file not found: {path}")
    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        _validate_columns(reader.fieldnames or [], required_columns, path)
        return [dict(row) for row in reader]


def _write_csv(path: Path, rows: list[Row], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows([{column: row.get(column, "") for column in columns} for row in rows])


def clean_text_frame(rows: list[Row]) -> list[Row]:
    """Clean, validate, and deduplicate text phishing rows."""
    cleaned: list[Row] = []
    seen: set[str] = set()
    for row in rows:
        text = normalize_whitespace(row.get("text"))
        label = normalize_whitespace(row.get("label")).lower()
        if not text or label not in ALLOWED_LABELS or text in seen:
            continue
        seen.add(text)
        cleaned.append(
            {
                "text": text,
                "label": label,
                "source": normalize_whitespace(row.get("source")) or "legacy_starter",
                "category": normalize_whitespace(row.get("category")) or "legacy_starter",
                "notes": normalize_whitespace(row.get("notes")),
            }
        )
    return cleaned


def clean_url_frame(rows: list[Row]) -> list[Row]:
    """Clean, validate, and deduplicate URL phishing rows."""
    cleaned: list[Row] = []
    seen: set[str] = set()
    for row in rows:
        url = normalize_whitespace(row.get("url"))
        label = normalize_whitespace(row.get("label")).lower()
        if not url or label not in ALLOWED_LABELS or url in seen:
            continue
        seen.add(url)
        cleaned.append(
            {
                "url": url,
                "label": label,
                "source": normalize_whitespace(row.get("source")) or "legacy_starter",
                "category": normalize_whitespace(row.get("category")) or "legacy_starter",
                "date_added": normalize_whitespace(row.get("date_added")),
            }
        )
    return cleaned


def balance_classes(rows: list[Row], label_column: str = "label") -> list[Row]:
    """Downsample classes to the smaller class while keeping both classes."""
    grouped: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        grouped[row[label_column]].append(row)
    if not ALLOWED_LABELS.issubset(grouped):
        raise ValueError(f"Both classes must be present before balancing; got { {k: len(v) for k, v in grouped.items()} }")
    minimum = min(len(grouped[label]) for label in ALLOWED_LABELS)
    if minimum <= 0:
        raise ValueError("Cannot balance dataset because one class is empty")
    balanced: list[Row] = []
    for label in sorted(ALLOWED_LABELS):
        first_column = "text" if "text" in grouped[label][0] else "url"
        balanced.extend(sorted(grouped[label], key=lambda row: row[first_column])[:minimum])
    return balanced


def _print_distribution(name: str, rows: list[Row]) -> None:
    print(f"{name}: {len(rows)} rows | {dict(Counter(row['label'] for row in rows))}")


def build_datasets(data_dir: Path) -> None:
    """Build processed master datasets and final training CSVs."""
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"

    text_existing = _read_csv(data_dir / "phishing_dataset.csv", TEXT_FINAL_COLUMNS)
    text_raw = _read_csv(raw_dir / "synthetic_text_examples.csv", TEXT_MASTER_COLUMNS)
    text_master = balance_classes(clean_text_frame([*text_raw, *text_existing]))

    url_existing = _read_csv(data_dir / "url_dataset.csv", URL_FINAL_COLUMNS)
    url_raw = _read_csv(raw_dir / "synthetic_url_examples.csv", URL_MASTER_COLUMNS)
    url_master = balance_classes(clean_url_frame([*url_raw, *url_existing]))

    text_master_path = processed_dir / "phishing_dataset_master.csv"
    url_master_path = processed_dir / "url_dataset_master.csv"
    text_final_path = data_dir / "phishing_dataset.csv"
    url_final_path = data_dir / "url_dataset.csv"

    _write_csv(text_master_path, text_master, TEXT_MASTER_COLUMNS)
    _write_csv(url_master_path, url_master, URL_MASTER_COLUMNS)
    _write_csv(text_final_path, text_master, TEXT_FINAL_COLUMNS)
    _write_csv(url_final_path, url_master, URL_FINAL_COLUMNS)

    _print_distribution(str(text_master_path), text_master)
    _print_distribution(str(text_final_path), text_master)
    _print_distribution(str(url_master_path), url_master)
    _print_distribution(str(url_final_path), url_master)


def main() -> None:
    build_datasets(Path(__file__).resolve().parents[1] / "data")


if __name__ == "__main__":
    main()
