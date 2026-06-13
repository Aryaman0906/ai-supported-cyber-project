# Local Gmail Polling Mode (No Billing Required)

This mode is for a personal/local demo that uses only Gmail API and optionally Drive API through local OAuth files. It does **not** require Cloud Run, Pub/Sub, Firestore, Secret Manager, or Cloud Scheduler.

## What it does

```text
Local terminal command
→ Gmail API list latest INBOX messages
→ skip messages already labeled AI-Cyber/Scanned
→ fetch message metadata/body
→ extract sender, subject, snippet, plain text body, URLs
→ run local text/URL risk engine when models are available
→ apply AI-Cyber labels in Gmail
→ save privacy-aware scan metadata locally
→ generate Markdown/CSV daily reports under reports/generated/YYYY-MM-DD/
```

The worker never opens links, downloads attachments, sends replies, deletes email, or performs scanning/exploitation.

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
