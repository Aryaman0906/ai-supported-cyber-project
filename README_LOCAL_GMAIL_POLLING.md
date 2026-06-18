# Local Gmail Polling Mode

This document describes the local scheduled Gmail polling workflow for the project.

## Architecture

```text
Windows Task Scheduler
→ local Gmail polling worker
→ Gmail API scan
→ AI-Cyber labels
→ Markdown/CSV/XLSX reports
→ optional Google Drive backup
```

This is local scheduled polling, not full cloud-native real-time monitoring.

## Local files

Keep private local configuration out of Git:

- `credentials.json`
- `token.json`
- `.env`
- `.env.local`
- `.local/`
- `reports/generated/`

## Drive upload setup

Do not commit a real Drive folder URL or folder ID. Store it only in a local ignored config file or environment variable.

Example local `.env`:

```text
DRIVE_REPORT_FOLDER=YOUR_PRIVATE_DRIVE_FOLDER_URL_OR_ID
LOCAL_ADMIN_TOKEN=YOUR_RANDOM_LOCAL_ADMIN_TOKEN
```

Manual upload command with placeholder only:

```powershell
python -m api.gmail_poll_worker --report-today --upload-drive --drive-folder "YOUR_PRIVATE_DRIVE_FOLDER_URL_OR_ID"
```

Expected successful output includes:

```text
GMAIL POLLING REPORT GENERATED
DRIVE UPLOAD COMPLETE
Markdown URL: ...
CSV URL     : ...
XLSX URL    : ...
```

## Dashboard security

Protected local endpoints require the `X-Local-Admin-Token` header. Generate the token locally and keep it out of Git.

## Task Scheduler proof

For final submission, add redacted proof only:

- Task Scheduler overview and trigger/action screenshots.
- Local reports folder showing `.md`, `.csv`, `.xlsx` files.
- Google Drive folder screenshot with private IDs blurred.
- Gmail labels screenshot with addresses and subjects blurred.
- Redacted `task-log.txt` success output.

## Safety notes

- Use only accounts you own or have permission to analyze.
- Do not commit real inbox data, OAuth files, logs, generated reports, Drive IDs, or report URLs.
- The tool applies labels only; it does not delete, forward, reply, exploit, or open links.
