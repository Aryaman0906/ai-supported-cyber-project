"""Watch a local sample log file and triage new lines in real time.

This script is defensive and local-only. It is intended for sanitized test logs,
not production logs or systems you do not own/have permission to monitor.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from api.log_analyzer import LogAnalyzer

DEFAULT_LOG_PATH = Path("data/sample_logs.log")


class LogFileTailer(FileSystemEventHandler):
    """Watch one log file and analyze lines appended to it."""

    def __init__(self, log_path: Path, analyzer: LogAnalyzer) -> None:
        self.log_path = log_path.resolve()
        self.analyzer = analyzer
        self.position = self.log_path.stat().st_size if self.log_path.exists() else 0

    def on_modified(self, event) -> None:  # type: ignore[override]
        """Handle watchdog file modification events."""
        if Path(event.src_path).resolve() != self.log_path:
            return

        with self.log_path.open("r", encoding="utf-8") as log_file:
            log_file.seek(self.position)
            new_lines = log_file.readlines()
            self.position = log_file.tell()

        for line in new_lines:
            cleaned_line = line.strip()
            if not cleaned_line:
                continue

            result = self.analyzer.analyze_line(cleaned_line)
            if result.risk_level in {"medium", "high"}:
                print(
                    f"ALERT risk={result.risk_level} verdict={result.verdict} "
                    f"score={result.risk_score} ip={result.parsed['ip']} "
                    f"path={result.parsed['path']} reasons={'; '.join(result.reasons)}"
                )
            else:
                print(
                    f"OK risk={result.risk_level} verdict={result.verdict} "
                    f"ip={result.parsed['ip']} path={result.parsed['path']}"
                )


def main() -> None:
    """Start watchdog monitoring for a sanitized local log file."""
    parser = argparse.ArgumentParser(description="Monitor a sanitized sample log file.")
    parser.add_argument(
        "--file",
        default=str(DEFAULT_LOG_PATH),
        help="Path to the local sample log file to watch.",
    )
    args = parser.parse_args()

    log_path = Path(args.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)

    analyzer = LogAnalyzer()
    event_handler = LogFileTailer(log_path, analyzer)
    observer = Observer()
    observer.schedule(event_handler, str(log_path.parent), recursive=False)
    observer.start()

    print(f"Watching {log_path} for new sanitized log lines. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
