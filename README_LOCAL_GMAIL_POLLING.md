# Local Gmail Polling Mode (No Billing Required)

This mode is for a personal/local demo that uses Gmail API and Drive API through local OAuth files. It does **not** require Cloud Run, Pub/Sub, Firestore, Secret Manager, or Cloud Scheduler.

## What it does

```text
Windows Task Scheduler or local terminal command
→ Gmail API list latest INBOX messages
→ skip messages already labeled AI-Cyber/Scanned
→ fetch message metadata/body
→ extract sender, subject, snippet, plain text body, URLs
→ run local text/URL risk engine when models are available
→ apply AI-Cyber labels in Gmail
→ save privacy-aware scan metadata locally
→ generate Markdown/CSV daily reports under reports/generated/YYYY-MM-DD/
→ upload the Markdown/CSV reports to the configured Google Drive folder
```

The worker never opens links, downloads attachments, sends replies, deletes email, or performs scanning/exploitation.

## Target Drive folder

The scheduled batch file is configured to upload daily reports to this folder:

```text
https://drive.google.com/drive/folders/1Ko8e6ldd3TasM-JQXpJO0wyYJ8S4u8EM?usp=drive_link
```

The worker also accepts either a Drive folder URL or a raw folder ID through `--drive-folder`.

## Files used locally

Place these files in the project root:

- `credentials.json` — OAuth client JSON downloaded from Google Cloud Console.
- `token.json` — created automatically after first browser login.

Both files are ignored by Git.

## Required OAuth scopes

The local worker uses these scopes:

- `https://www.googleapis.com/auth/gmail.modify`
- `https://www.googleapis.com/auth/drive.file`

It does **not** use the full `https://mail.google.com/` scope.

If you created `token.json` before adding Drive support, delete `token.json` and run the worker again so Google asks for the Drive permission too.

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

On first run, your browser opens for Gmail/Drive consent. After login, `token.json` is saved locally.

### 6. Run continuous polling manually

```powershell
python -m api.gmail_poll_worker --loop --interval 300 --limit 10
```

This checks the latest 10 inbox messages every 300 seconds.

### 7. Generate today's local report

```powershell
python -m api.gmail_poll_worker --report-today
```

Reports are written to:

```text
reports/generated/YYYY-MM-DD/gmail_poll_report.md
reports/generated/YYYY-MM-DD/gmail_poll_report.csv
```

### 8. Generate today's report and upload it to Drive

```powershell
python -m api.gmail_poll_worker --report-today --upload-drive --drive-folder "https://drive.google.com/drive/folders/1Ko8e6ldd3TasM-JQXpJO0wyYJ8S4u8EM?usp=drive_link"
```

Expected terminal output includes:

```text
GMAIL POLLING REPORT GENERATED
DRIVE UPLOAD COMPLETE
Markdown URL: ...
CSV URL     : ...
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

## Privacy and safety

- Do not use this on accounts you do not own or have explicit permission to analyze.
- Do not commit `credentials.json` or `token.json`.
- Do not paste or store passwords, session tokens, or private reset links.
- Full email bodies are not stored in local reports; the worker stores short previews and metadata.
- Attachments are ignored and are not downloaded.
- Links are extracted as strings but are not opened.
- The tool is an assistive signal only; human review is required.
- Drive upload sends only the generated Markdown/CSV report files to the configured Drive folder.

## Troubleshooting

### `credentials.json was not found`

Download an OAuth client JSON from Google Cloud Console, rename it to `credentials.json`, and place it in the project root.

### Browser does not open

Copy the URL printed by the OAuth flow into your browser manually.

### `invalid_grant`

Delete `token.json` and run the worker again to complete OAuth from scratch.

### Gmail API 403

Confirm Gmail API is enabled, your account is added as a test user in OAuth consent, and the OAuth client/scopes are correct.

### Drive upload returns 403

Check these items:

1. Drive API is enabled in Google Cloud Console.
2. The same Google account used during OAuth has access to the target folder.
3. Delete `token.json` and run again so the `drive.file` scope is granted.
4. If the folder was created outside the app and Drive still refuses access, create or select a folder that the OAuth user can write to, then pass its folder link with `--drive-folder`.

### Messages are skipped

Messages already labeled `AI-Cyber/Scanned` are skipped by default. Use `--force` if you intentionally want to re-scan.

### Reports are empty

Run a scan first, then run:

```powershell
python -m api.gmail_poll_worker --report-today --upload-drive
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

If you automate polling with Windows Task Scheduler, configure the task to run your batch file, for example `run_gmail_poll_once.bat`, every few minutes.

The committed batch file now runs both steps:

```text
python -m api.gmail_poll_worker --once --limit 20
python -m api.gmail_poll_worker --report-today --upload-drive --drive-folder "<target Drive folder>"
```

To verify it is working:

1. Open **Task Scheduler**.
2. Find your Gmail polling task.
3. Confirm **Last Run Time** updates.
4. Confirm **Last Run Result** is `0x0`.
5. Check that `reports/generated/task-log.txt` is being updated.
6. Confirm `task-log.txt` contains `DRIVE UPLOAD COMPLETE`.
7. Open the Drive folder and confirm the latest Markdown/CSV report files appear.
8. Open the local dashboard and click **Load latest log**.

## Reading task-log.txt manually

PowerShell:

```powershell
Get-Content .\reports\generated\task-log.txt -Tail 100
```

FastAPI endpoint:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/polling/latest-log
```
