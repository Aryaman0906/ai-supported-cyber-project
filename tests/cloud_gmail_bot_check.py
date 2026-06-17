"""Cloud-readiness checks for the Gmail Security Bot."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def require_file(path: str) -> str:
    full = ROOT / path
    assert full.is_file(), f"Missing {path}"
    return full.read_text(encoding="utf-8")

def main() -> None:
    dockerfile = require_file("Dockerfile")
    assert "0.0.0.0" in dockerfile and "${PORT:-8080}" in dockerfile
    main_py = require_file("api/main.py")
    for endpoint in ["/gmail/auth/start", "/gmail/pubsub/push", "/gmail/watch/start", "/gmail/scan-now", "/reports/generate-daily", "/tasks/daily-maintenance"]:
        assert endpoint in main_py, f"Missing endpoint {endpoint}"
    env = require_file(".env.example")
    for key in ["GOOGLE_CLOUD_PROJECT", "GMAIL_PUBSUB_TOPIC", "TOKEN_ENCRYPTION_KEY", "PUBSUB_PUSH_TOKEN", "TASK_SHARED_SECRET"]:
        assert key in env, f"Missing env var {key}"
    docs = require_file("README_CLOUD_RUN_GMAIL_BOT.md")
    for phrase in ["Gmail API", "Pub/Sub", "Cloud Run", "Firestore", "Secret Manager", "Drive API", "Cloud Scheduler", "gmail-api-push@system.gserviceaccount.com"]:
        assert phrase in docs, f"Missing docs phrase {phrase}"
    print("Cloud Gmail bot readiness checks passed.")

if __name__ == "__main__": main()
