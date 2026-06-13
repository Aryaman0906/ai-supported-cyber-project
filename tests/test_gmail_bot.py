from __future__ import annotations

import base64, json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.gmail_client import labels_for_risk, parse_gmail_message
from api.gmail_scanner import decode_pubsub_push
from api.report_writer import generate_csv_report, generate_markdown_report
from api.risk_engine import GmailRiskEngine
from api.storage import InMemoryStorage

class FakeTextResult:
    prediction = "phishing"; confidence = 0.91; reasons = ["text reason"]
class FakeTextAnalyzer:
    is_loaded = True
    def analyze(self, text): return FakeTextResult()
class FakeUrlResult:
    verdict = "legitimate"; score = 0.55; risk_level = "low"; reasons = ["url reason"]
class FakeUrlAnalyzer:
    is_loaded = True
    def analyze(self, url, include_external_checks=False): return FakeUrlResult()

def test_pubsub_payload_decode():
    payload = {"emailAddress": "user@example.com", "historyId": "123"}
    data = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    assert decode_pubsub_push({"message": {"data": data}}) == payload

def test_risk_engine_with_mocked_analyzers():
    result = GmailRiskEngine(FakeTextAnalyzer(), FakeUrlAnalyzer()).analyze("urgent verify", ["https://example.com"])
    assert result.risk_level == "high"
    assert result.text_prediction == "phishing"
    assert result.url_results[0]["url"] == "https://example.com"

def test_gmail_message_parsing():
    body = base64.urlsafe_b64encode(b"Hello visit https://example.com/path").decode().rstrip("=")
    message = {"id":"m1","threadId":"t1","internalDate":"1710000000000","labelIds":["INBOX"],"snippet":"snippet","payload":{"headers":[{"name":"From","value":"Sender <sender@example.com>"},{"name":"Subject","value":"Test https://url.test"}],"mimeType":"text/plain","body":{"data":body}}}
    parsed = parse_gmail_message(message)
    assert parsed.message_id == "m1"
    assert parsed.sender_domain == "example.com"
    assert "https://example.com/path" in parsed.urls

def test_label_selection_unknown_maps_to_medium():
    labels = {"scanned":"S","low":"L","medium":"M","high":"H"}
    assert labels_for_risk("unknown", labels) == ["S", "M"]
    assert labels_for_risk("high", labels) == ["S", "H"]

def test_report_generation():
    results = [{"message_id":"m1","date":"2026-06-13","sender_domain":"bad.test","risk_level":"high","score":0.9,"url_domains":["bad.test"],"reasons":["reason"]}]
    assert "High risk: 1" in generate_markdown_report("2026-06-13", results)
    assert "bad.test" in generate_csv_report(results)

def test_storage_in_memory():
    storage = InMemoryStorage()
    storage.save_account("u@example.com", {"last_history_id":"1"})
    storage.save_scan_result("u@example.com", "m1", {"date":"2026-06-13", "risk_level":"low"})
    assert storage.get_account("u@example.com")["last_history_id"] == "1"
    assert len(storage.get_scan_results_for_date("2026-06-13", "u@example.com")) == 1
