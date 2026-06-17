from __future__ import annotations

import base64, json, os, socket, types, zipfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.gmail_client import labels_for_risk, parse_gmail_message
from api.gmail_scanner import decode_pubsub_push
from api.report_writer import generate_csv_report, generate_markdown_report, generate_xlsx_report_bytes
from api.risk_engine import GmailRiskEngine, RiskResult
from api.storage import InMemoryStorage



def gmail_b64(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")

def gmail_message(payload: dict, snippet: str = "snippet") -> dict:
    payload.setdefault("headers", [{"name":"From","value":"Sender <sender@example.com>"},{"name":"Subject","value":"Test https://url.test"}])
    return {"id":"m1","threadId":"t1","internalDate":"1710000000000","labelIds":["INBOX"],"snippet":snippet,"payload":payload}

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



def test_html_only_gmail_message_parsing_preserves_text_and_links():
    html = """<html><head><style>.x{display:none}</style><script>alert('x')</script></head>
    <body><p>Verify your account</p><a href="https://safe.example.test/login">Open portal</a></body></html>"""
    message = gmail_message({"mimeType":"text/html","body":{"data":gmail_b64(html)}})
    parsed = parse_gmail_message(message)
    assert "Verify your account" in parsed.body_text
    assert "Open portal" in parsed.body_text
    assert "alert" not in parsed.body_text
    assert "https://safe.example.test/login" in parsed.urls

def test_multipart_alternative_prefers_plain_text():
    message = gmail_message({
        "mimeType":"multipart/alternative",
        "parts":[
            {"mimeType":"text/plain","body":{"data":gmail_b64("Plain body https://plain.example.test")}},
            {"mimeType":"text/html","body":{"data":gmail_b64("<p>HTML body</p><a href='https://html.example.test'>link</a>")}},
        ],
    })
    parsed = parse_gmail_message(message)
    assert "Plain body" in parsed.body_text
    assert "HTML body" not in parsed.body_text
    assert "https://plain.example.test" in parsed.urls

def test_nested_multipart_html_parsing():
    message = gmail_message({
        "mimeType":"multipart/mixed",
        "parts":[
            {"mimeType":"multipart/alternative","parts":[
                {"mimeType":"text/html","body":{"data":gmail_b64("<div>Nested HTML</div><a href='https://nested.example.test/path'>Nested link</a>")}},
            ]},
            {"filename":"invoice.pdf","mimeType":"application/pdf","body":{"attachmentId":"att-1"}},
        ],
    })
    parsed = parse_gmail_message(message)
    assert "Nested HTML" in parsed.body_text
    assert "https://nested.example.test/path" in parsed.urls
    assert parsed.has_attachments is True

def test_label_selection_unknown_maps_to_medium():
    labels = {"scanned":"S","low":"L","medium":"M","high":"H"}
    assert labels_for_risk("unknown", labels) == ["S", "M"]
    assert labels_for_risk("high", labels) == ["S", "H"]

def test_report_generation():
    results = [{"message_id":"m1","date":"2026-06-13","sender_domain":"bad.test","risk_level":"high","score":0.9,"url_domains":["bad.test"],"reasons":["reason"]}]
    assert "High risk: 1" in generate_markdown_report("2026-06-13", results)
    assert "bad.test" in generate_csv_report(results)
    xlsx_bytes = generate_xlsx_report_bytes(results)
    assert xlsx_bytes.startswith(b"PK")
    with zipfile.ZipFile(__import__("io").BytesIO(xlsx_bytes)) as workbook:
        assert "xl/worksheets/sheet1.xml" in workbook.namelist()

def test_storage_in_memory():
    storage = InMemoryStorage()
    storage.save_account("u@example.com", {"last_history_id":"1"})
    storage.save_scan_result("u@example.com", "m1", {"date":"2026-06-13", "risk_level":"low"})
    assert storage.get_account("u@example.com")["last_history_id"] == "1"
    assert len(storage.get_scan_results_for_date("2026-06-13", "u@example.com")) == 1

from api.gmail_poll_worker import ScanLock, format_report_output, format_scan_summary, generate_local_report, parse_drive_folder_id, scan_latest_inbox, upload_report_files_to_drive

class FakeExecute:
    def __init__(self, value=None): self.value = value or {}
    def execute(self): return self.value

class FakeMessages:
    def __init__(self):
        self.modified = []
        body = base64.urlsafe_b64encode(b"Please verify at http://example-risk.test/login").decode().rstrip("=")
        self.message = {"id":"poll1","threadId":"th1","internalDate":"1710000000000","labelIds":["INBOX"],"snippet":"verify login","payload":{"headers":[{"name":"From","value":"Tester <sender@example.test>"},{"name":"Subject","value":"Urgent verify"}],"mimeType":"text/plain","body":{"data":body}}}
    def list(self, **kwargs): return FakeExecute({"messages":[{"id":"poll1"}]})
    def get(self, **kwargs): return FakeExecute(self.message)
    def modify(self, **kwargs): self.modified.append(kwargs); return FakeExecute({})

class FakeLabels:
    def __init__(self):
        self.labels = [{"name":"AI-Cyber/Scanned","id":"S"},{"name":"AI-Cyber/Low","id":"L"},{"name":"AI-Cyber/Medium","id":"M"},{"name":"AI-Cyber/High","id":"H"}]
    def list(self, **kwargs): return FakeExecute({"labels": self.labels})
    def create(self, **kwargs): return FakeExecute({"id":"NEW"})

class FakeUsers:
    def __init__(self): self._messages = FakeMessages(); self._labels = FakeLabels()
    def messages(self): return self._messages
    def labels(self): return self._labels

class FakeGmailService:
    def __init__(self): self._users = FakeUsers()
    def users(self): return self._users

class MediumRiskEngine:
    def analyze(self, text, urls):
        return RiskResult("medium", 0.7, "phishing", 0.7, [], ["mock medium"], "safe")

def test_local_polling_dry_run_logic(tmp_path):
    service = FakeGmailService()
    storage = InMemoryStorage()
    summary = scan_latest_inbox(service, storage, MediumRiskEngine(), limit=5, dry_run=True)
    assert summary["scanned_count"] == 1
    assert summary["medium_count"] == 1
    assert service.users().messages().modified == []

def test_local_report_generation(tmp_path, monkeypatch):
    monkeypatch.setattr("api.gmail_poll_worker.REPORT_ROOT", tmp_path)
    storage = InMemoryStorage()
    storage.save_scan_result("local-gmail", "m1", {"date":"2026-06-13", "risk_level":"high", "sender_domain":"bad.test", "score":0.9, "url_domains":["bad.test"], "reasons":["reason"]})
    output = generate_local_report(storage, "2026-06-13")
    assert Path(output["markdown_path"]).exists()
    assert Path(output["csv_path"]).exists()
    assert Path(output["xlsx_path"]).exists()

def test_local_polling_console_format_hides_skipped_ids():
    summary = {
        "scanned_count": 1,
        "skipped_count": 1,
        "high_count": 1,
        "medium_count": 0,
        "low_count": 0,
        "unknown_count": 0,
        "results": [
            {
                "message_id": "new-message",
                "sender": "Demo <demo@example.test>",
                "subject_preview": "Hackathon demo",
                "risk_level": "high",
                "score": 0.91,
                "url_domains": ["example.test"],
                "labels_applied": ["AI-Cyber/Scanned", "AI-Cyber/High"],
                "reasons": ["Mock reason"],
            },
            {"message_id": "skipped-message-id", "skipped": True, "reason": "Already labeled"},
        ],
    }
    output = format_scan_summary(summary)
    assert "GMAIL POLLING TASK RESULT" in output
    assert "Scanned emails : 1" in output
    assert "Skipped emails : 1" in output
    assert "skipped-message-id" not in output
    assert "Mock reason" in output

def test_local_report_console_format():
    output = format_report_output({"date": "2026-06-15", "markdown_path": "reports/generated/2026-06-15/report.md", "csv_path": "reports/generated/2026-06-15/report.csv", "xlsx_path": "reports/generated/2026-06-15/report.xlsx"})
    assert "GMAIL POLLING REPORT GENERATED" in output
    assert "reports/generated/2026-06-15/report.md" in output


def test_drive_folder_url_and_raw_id_parsing():
    folder_id = "1Ko8e6ldd3TasM-JQXpJO0wyYJ8S4u8EM"
    url = f"https://drive.google.com/drive/folders/{folder_id}?usp=drive_link"
    assert parse_drive_folder_id(url) == folder_id
    assert parse_drive_folder_id(folder_id) == folder_id



def test_drive_upload_behavior_mocked(tmp_path, monkeypatch):
    markdown = tmp_path / "gmail_poll_report.md"
    csv_path = tmp_path / "gmail_poll_report.csv"
    xlsx_path = tmp_path / "gmail_poll_report.xlsx"
    markdown.write_text("# report", encoding="utf-8")
    csv_path.write_text("message_id", encoding="utf-8")
    xlsx_path.write_bytes(b"PK fake")

    class FakeMediaFileUpload:
        def __init__(self, path, mimetype, resumable=False):
            self.path = path
            self.mimetype = mimetype

    class FakeCreate:
        def __init__(self, body):
            self.body = body
        def execute(self):
            return {"id": self.body["name"], "webViewLink": f"https://drive.test/{self.body['name']}"}

    class FakeFiles:
        def create(self, body, media_body, fields):
            return FakeCreate(body)

    class FakeDriveService:
        def files(self):
            return FakeFiles()

    fake_http = types.ModuleType("googleapiclient.http")
    fake_http.MediaFileUpload = FakeMediaFileUpload
    monkeypatch.setitem(sys.modules, "googleapiclient", types.ModuleType("googleapiclient"))
    monkeypatch.setitem(sys.modules, "googleapiclient.http", fake_http)
    monkeypatch.setattr("api.gmail_poll_worker.build_local_drive_service", lambda: FakeDriveService())

    result = upload_report_files_to_drive({
        "markdown_path": str(markdown),
        "csv_path": str(csv_path),
        "xlsx_path": str(xlsx_path),
    }, "https://drive.google.com/drive/folders/folder123?usp=drive_link")

    assert result["markdown"]["webViewLink"].endswith("gmail_poll_report.md")
    assert result["csv"]["webViewLink"].endswith("gmail_poll_report.csv")
    assert result["xlsx"]["webViewLink"].endswith("gmail_poll_report.xlsx")

def test_report_console_format_includes_drive_urls():
    output = format_report_output({
        "date": "2026-06-16",
        "markdown_path": "reports/generated/2026-06-16/gmail_poll_report.md",
        "csv_path": "reports/generated/2026-06-16/gmail_poll_report.csv",
        "xlsx_path": "reports/generated/2026-06-16/gmail_poll_report.xlsx",
        "drive": {
            "markdown": {"webViewLink": "https://drive.google.com/file/d/md"},
            "csv": {"webViewLink": "https://drive.google.com/file/d/csv"},
            "xlsx": {"webViewLink": "https://drive.google.com/file/d/xlsx"},
        },
    })
    assert "GMAIL POLLING REPORT GENERATED" in output
    assert "DRIVE UPLOAD COMPLETE" in output
    assert "Markdown URL: https://drive.google.com/file/d/md" in output
    assert "CSV URL     : https://drive.google.com/file/d/csv" in output
    assert "XLSX URL    : https://drive.google.com/file/d/xlsx" in output

from api import polling_dashboard

def test_polling_status_missing_and_present_files(tmp_path, monkeypatch):
    credentials = tmp_path / "credentials.json"
    token = tmp_path / "token.json"
    reports = tmp_path / "reports" / "generated"
    monkeypatch.setattr(polling_dashboard, "CREDENTIALS_PATH", credentials)
    monkeypatch.setattr(polling_dashboard, "TOKEN_PATH", token)
    monkeypatch.setattr(polling_dashboard, "REPORTS_DIR", reports)
    monkeypatch.setattr(polling_dashboard, "TASK_LOG_PATH", reports / "task-log.txt")
    missing = polling_dashboard.polling_status()
    assert missing["credentials_json_exists"] is False
    credentials.write_text("{}")
    token.write_text("{}")
    reports.mkdir(parents=True)
    present = polling_dashboard.polling_status()
    assert present["credentials_json_exists"] is True
    assert present["token_json_exists"] is True
    assert present["reports_generated_exists"] is True

def test_polling_report_listing_ignores_string_folder(tmp_path):
    reports = tmp_path / "reports"
    (reports / "string").mkdir(parents=True)
    dated = reports / "2026-06-13"
    dated.mkdir()
    (dated / "gmail_poll_report.md").write_text("# report")
    (dated / "gmail_poll_report.csv").write_text("message_id")
    rows = polling_dashboard.list_report_folders(reports)
    assert [row["date"] for row in rows] == ["2026-06-13"]
    assert rows[0]["markdown_files"]
    assert rows[0]["csv_files"]
    assert "xlsx_files" in rows[0]

def test_polling_latest_log_reads_last_100_lines(tmp_path):
    log = tmp_path / "task-log.txt"
    log.write_text("\n".join(f"line {i}" for i in range(150)))
    result = polling_dashboard.latest_log(log_path=log)
    assert result["exists"] is True
    assert len(result["lines"]) == 100
    assert result["lines"][0] == "line 50"

def test_polling_scan_endpoint_helper_mocked(monkeypatch):
    def fake_run_once(limit, dry_run=False):
        return {"scanned_count": limit, "dry_run": dry_run}
    monkeypatch.setattr(polling_dashboard.gmail_poll_worker, "run_once", fake_run_once)
    assert polling_dashboard.run_scan_now(limit=20, dry_run=True) == {"scanned_count": 20, "dry_run": True}


def test_scan_lock_prevents_overlap(tmp_path):
    lock_path = tmp_path / "scan.lock"
    metadata = {"pid": os.getpid(), "hostname": socket.gethostname(), "started_at": "2026-06-16T00:00:00+00:00"}
    lock_path.write_text(json.dumps(metadata), encoding="utf-8")
    with ScanLock(lock_path=lock_path, stale_seconds=3600) as lock:
        assert lock.acquired is False
    assert lock_path.exists()
