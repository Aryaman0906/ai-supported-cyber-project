# Local Gmail Polling Mode (No Billing Required)

This mode is for a personal/local demo that uses only Gmail API and optionally Drive API through local OAuth files. It does **not** require Cloud Run, Pub/Sub, Firestore, Secret Manager, or Cloud Scheduler.

## What it does

```text
Local terminal command
→ Gmail API list latest INBOX messages
→ skip messages already labeled AI-Cyber/Scanned
→ fetch message metadata/body
→ extract sender, subject, snippet, plain-text or HTML body text, URLs
→ run local text/URL risk engine when models are available
→ apply AI-Cyber labels in Gmail
→ save privacy-aware scan metadata locally
→ generate Markdown/CSV/XLSX daily reports under reports/generated/YYYY-MM-DD/
→ optionally upload both report files to a selected Google Drive folder
```

The worker supports plain-text and HTML Gmail bodies. When only HTML is available, it converts visible text to readable text, strips script/style content, and preserves visible HTTP/HTTPS links as analysis signals. The worker never opens links, downloads attachments, sends replies, deletes email, or performs scanning/exploitation.

## Files used locally

Place these files in the project root:

- `credentials.json` — OAuth client JSON downloaded from Google Cloud Console.
- `token.json` — created automatically after first browser login.

Both files are ignored by Git.

## Required OAuth scopes

The local worker uses the same minimum scopes as the Cloud Run bot:

- `https://www.googleapis.com/auth/gmail.modify`
- `https://www.googleapis.com/auth/drive.file`

It does **not** use the full `https://mail.google.com/` scope.

## Windows PowerShell setup

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If activation is blocked, run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Train local models

```powershell
python -m train.train_text_model
python -m train.train_url_model
```

If model files are missing, the worker still runs but returns `unknown` analysis results and asks for manual review.

### 4. Create OAuth client

1. Open Google Cloud Console.
2. Enable Gmail API and Drive API.
3. Configure OAuth consent for a personal/test app.
4. Create an OAuth client. A Desktop app client is easiest for local polling.
5. Download the client JSON.
6. Rename it to `credentials.json`.
7. Place it in the project root.

### 5. Run one scan

```powershell
python -m api.gmail_poll_worker --once --limit 5
```

On first run, your browser opens for Gmail consent. After login, `token.json` is saved locally.

### 6. Run continuous polling

```powershell
python -m api.gmail_poll_worker --loop --interval 300 --limit 10
```

This checks the latest 10 inbox messages every 300 seconds.

### 7. Generate today's report

```powershell
python -m api.gmail_poll_worker --report-today
```

Reports are written to:

```text
reports/generated/YYYY-MM-DD/gmail_poll_report.md
reports/generated/YYYY-MM-DD/gmail_poll_report.csv
reports/generated/YYYY-MM-DD/gmail_poll_report.xlsx
```

### 8. Generate and upload today's report to Google Drive

Use either a Google Drive folder URL or the raw folder ID. The local worker parses URLs of the form `https://drive.google.com/drive/folders/<FOLDER_ID>?usp=drive_link`.

```powershell
python -m api.gmail_poll_worker --report-today --upload-drive --drive-folder "https://drive.google.com/drive/folders/1Ko8e6ldd3TasM-JQXpJO0wyYJ8S4u8EM?usp=drive_link"
```

Expected successful console output includes:

```text
GMAIL POLLING REPORT GENERATED
DRIVE UPLOAD COMPLETE
Markdown URL: ...
CSV URL     : ...
XLSX URL    : ...
```

## Optional dry run

Use `--dry-run` to analyze and save local metadata without applying Gmail labels:

```powershell
python -m api.gmail_poll_worker --once --limit 5 --dry-run
```

## Gmail labels applied

The worker creates and applies:

- `AI-Cyber/Scanned`
- `AI-Cyber/Low`
- `AI-Cyber/Medium`
- `AI-Cyber/High`

If analysis is unknown, it applies medium review behavior so you can inspect manually.


## Medium-priority project tracker

| Priority | Task                                                 | Status          |
| -------- | ---------------------------------------------------- | --------------- |
| Medium   | Add HTML email parsing                               | Done in this PR |
| Medium   | Add overlap protection using lock file/process guard | Done in this PR |

## Scheduled scan overlap protection

The local scheduled scan uses an atomic lock file at `runtime/scan.lock` so Windows Task Scheduler cannot start two Gmail scans at the same time. The lock stores only PID, hostname, and start timestamp metadata. If a second scheduled run starts while another scan is active, it prints a clear skip message and exits safely with code `0`. Stale lock files are removed automatically when the recorded process is gone or the lock is older than the timeout.

This is still near-real-time scheduled polling, not full real-time Gmail push monitoring.

## Privacy and safety

- Do not use this on accounts you do not own or have explicit permission to analyze.
- Do not commit `credentials.json` or `token.json`.
- Do not paste or store passwords, session tokens, or private reset links.
- Full email bodies are not stored in local reports; the worker stores short previews and metadata.
- Attachments are ignored and are not downloaded.
- Links are extracted as strings but are not opened.
- The tool is an assistive signal only; human review is required.

## Troubleshooting

### `credentials.json was not found`

Download an OAuth client JSON from Google Cloud Console, rename it to `credentials.json`, and place it in the project root.

### Browser does not open

Copy the URL printed by the OAuth flow into your browser manually.

### `invalid_grant`

Delete `token.json` and run the worker again to complete OAuth from scratch.

### Gmail API 403

Confirm Gmail API is enabled, your account is added as a test user in OAuth consent, and the OAuth client/scopes are correct.

### Messages are skipped

Messages already labeled `AI-Cyber/Scanned` are skipped by default. Use `--force` if you intentionally want to re-scan.

### Reports are empty

Run a scan first, then run:

```powershell
python -m api.gmail_poll_worker --report-today
```

## Reference

This local OAuth approach follows the Google Gmail API Python quickstart pattern of using a local `credentials.json`, opening a browser for consent, and saving a local `token.json` for later runs: https://developers.google.com/workspace/gmail/api/quickstart/python

## Local FastAPI dashboard

Start the FastAPI backend:

```powershell
uvicorn api.main:app --reload
```

Start the static frontend in another PowerShell window:

```powershell
python -m http.server 8080 --directory frontend
```

Open:

```text
http://127.0.0.1:8080/index.html
```

Use the **Gmail Polling Bot** section to:

- Refresh local polling status.
- Check whether `credentials.json`, `token.json`, and `reports/generated/` exist.
- Run a scan now through `POST /polling/scan-now`.
- Generate today's report through `POST /polling/report-today`.
- Load `reports/generated/task-log.txt` through `GET /polling/latest-log`.
- List generated report folders through `GET /polling/reports`.

The dashboard never displays the contents of `credentials.json` or `token.json`.

## Verifying Windows Task Scheduler

If you automate polling with Windows Task Scheduler, keep using the existing `run_gmail_poll_hidden.vbs` → `run_gmail_poll_once.bat` workflow every few minutes. The batch file stays in the project directory, scans the latest 20 inbox messages, generates today's local report, and uploads the Markdown/CSV/XLSX report to the configured Drive folder.

To verify it is working:

1. Open **Task Scheduler**.
2. Find your Gmail polling task.
3. Confirm **Last Run Time** updates.
4. Confirm **Last Run Result** is `0x0`.
5. Check that `reports/generated/task-log.txt` is being updated.
6. Confirm the log includes `GMAIL POLLING REPORT GENERATED`, `DRIVE UPLOAD COMPLETE`, Markdown/CSV/XLSX URLs after a successful report upload.
7. Open the local dashboard and click **Load latest log**.

## Reading task-log.txt manually

PowerShell:

```powershell
Get-Content .\reports\generated\task-log.txt -Tail 100
```

FastAPI endpoint:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/polling/latest-log
```
