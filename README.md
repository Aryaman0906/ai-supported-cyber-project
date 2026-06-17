# AI-Assisted Defensive Cybersecurity Mini-Project

AI-assisted phishing analysis, URL analysis, log triage, and near-real-time local Gmail polling project for defensive cybersecurity learning.

> **Responsible-use scope:** This project is defensive only. It is designed for sanitized datasets, sample emails, test URLs, sample logs, and user-provided input. It must not be used to generate phishing content, steal credentials, attack websites, scrape real inboxes without permission, or perform harmful activity.

## Current Gmail demo architecture

The final Gmail demo uses **near-real-time local polling** with Windows Task Scheduler. It is not full real-time Gmail push monitoring and it is not a full cloud-native Cloud Run/Pub/Sub deployment.

Working local flow:

```text
Local Windows Task Scheduler
→ run_gmail_poll_hidden.vbs
→ run_gmail_poll_once.bat
→ api.gmail_poll_worker
→ Gmail API scan and AI/rule-assisted risk analysis
→ Gmail labels
→ Markdown, CSV, and XLSX reports
→ optional Google Drive upload
```

Cloud Run/Pub/Sub materials are future optional scope only. The working implementation is local scheduled automation with optional Drive backup/storage.

## What the project includes

- Text/email phishing detection using an offline-trained TF-IDF and Logistic Regression model.
- URL phishing analysis using explainable URL features and a Random Forest model.
- Optional external threat-intelligence checks when API keys are configured.
- Sanitized log triage for defensive sample log analysis.
- FastAPI endpoints for local real-time prediction demos.
- Browser frontend demo for text, URL, and log analysis.
- Local Gmail polling through Gmail API and OAuth.
- HTML and plain-text email body parsing.
- Gmail label application for scanned and risk-classified messages.
- Scheduled scan overlap protection through a lock file.
- Local report generation in Markdown, CSV, and XLSX formats.
- Optional Google Drive upload for generated reports.

## What the project does not claim

- It is not a production-grade SOC tool.
- It is not full real-time Gmail push monitoring.
- It is not fully cloud-native automation.
- It does not replace human review.
- It should not be connected to private inboxes, production logs, or real systems without clear permission.

## Project structure

```text
ai-supported-cyber-project/
├── api/                         # FastAPI app, analyzers, Gmail polling, report helpers
├── data/                        # Sanitized starter datasets and sample logs
├── frontend/                    # Local browser demo
├── models/                      # Locally trained model files, ignored when generated
├── report/                      # Responsible-use and project explanation files
├── reports/generated/           # Generated Gmail reports, ignored by Git
├── runtime/                     # Runtime lock files, ignored by Git
├── tests/                       # Local checks and pytest tests
├── train/                       # Offline training scripts
├── run_gmail_poll_once.bat      # Windows Task Scheduler batch entrypoint
├── run_gmail_poll_hidden.vbs    # Hidden Windows runner for scheduled task
├── requirements.txt
└── README.md
```

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Train the local models

```bash
python -m train.train_text_model
python -m train.train_url_model
```

Expected model files:

```text
models/text_phishing_model.joblib
models/url_phishing_model.joblib
```

## Run the FastAPI demo

```bash
uvicorn api.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Useful endpoints:

- `GET /health`
- `POST /analyze-text`
- `POST /analyze-url`
- `POST /analyze-log-line`

## Run the local frontend demo

Start FastAPI first, then open:

```text
frontend/index.html
```

Optional static server:

```bash
python -m http.server 8080 --directory frontend
```

Then open:

```text
http://127.0.0.1:8080
```

## Local Gmail polling setup

Place these OAuth files in the project root. They are intentionally ignored by Git:

```text
credentials.json
token.json
```

Run one local Gmail scan:

```powershell
python -m api.gmail_poll_worker --once --limit 5
```

Generate today's local reports:

```powershell
python -m api.gmail_poll_worker --report-today
```

Generate reports and upload them to Google Drive:

```powershell
python -m api.gmail_poll_worker --report-today --upload-drive --drive-folder "<GOOGLE_DRIVE_FOLDER_URL_OR_ID>"
```

For scheduled Drive upload, do **not** hardcode a real Drive folder URL or ID in `run_gmail_poll_once.bat`. Instead, create an ignored `.env` file in the project root or set a Windows environment variable:

```text
DRIVE_REPORT_FOLDER=<GOOGLE_DRIVE_FOLDER_URL_OR_ID>
```

The report workflow creates:

```text
reports/generated/YYYY-MM-DD/gmail_poll_report.md
reports/generated/YYYY-MM-DD/gmail_poll_report.csv
reports/generated/YYYY-MM-DD/gmail_poll_report.xlsx
```

## Windows Task Scheduler flow

The Windows scheduled workflow uses:

```text
run_gmail_poll_hidden.vbs
run_gmail_poll_once.bat
```

The batch file runs one scan, then generates the daily report. If `DRIVE_REPORT_FOLDER` is configured through an ignored `.env` file or a Windows environment variable, it also uploads the report files to Google Drive. If the variable is missing, it safely generates local reports only.

A lock file prevents overlapping scheduled scans:

```text
runtime/scan.lock
```

On Windows, stale lock cleanup uses timeout-based behavior instead of unsafe Unix-style PID probing.

## Reports and Google Drive

The correct report story is:

```text
Reports are generated locally and can be automatically uploaded to Google Drive by the scheduled local task.
```

Do not describe the project as fully cloud-based. The Drive upload is cloud backup/storage for reports created by local scheduled automation.

## Tests and validation

Run the main pytest suite:

```powershell
python -m pytest tests/test_gmail_bot.py -q
```

Run dependency-light project checks:

```powershell
python tests/phase_completion_check.py
python tests/cloud_gmail_bot_check.py
```

Useful manual proof commands:

```powershell
python -m api.gmail_poll_worker --once --limit 5
python -m api.gmail_poll_worker --report-today
.\run_gmail_poll_once.bat
```

## Files that must stay private

Do not commit real credentials, OAuth tokens, generated reports, logs, local state, lock files, model artifacts, Drive folder URLs, Drive folder IDs, or private email data. `.gitignore` is configured to keep the main local files out of Git.

Important ignored examples:

```text
credentials.json
token.json
.env
.local/
reports/generated/
reports/private/
runtime/
models/*.joblib
*.log
```

## Proof checklist for final submission

Add these screenshots or redacted outputs to your report/demo evidence:

1. Task Scheduler task list showing the configured scheduled task.
2. Task Scheduler trigger/action settings.
3. `task-log.txt` showing a successful scheduled run.
4. Local reports folder showing `.md`, `.csv`, and `.xlsx` files.
5. Google Drive folder showing uploaded report files.
6. Gmail labels showing scanned/risk-classified messages.
7. Terminal output showing tests/checks passing.
8. Redacted sample report output.

## Responsible-use and limitations

- Use sanitized data wherever possible.
- Do not publish real email bodies, private links, credentials, tokens, Drive folder URLs, Drive folder IDs, or personal data.
- Treat all model and rule outputs as assistive signals only.
- Human review is required before taking security action.
- Small starter datasets can produce false positives and false negatives.
- External threat-intelligence checks may share submitted URLs with third-party providers, so only use them with URLs you have permission to submit.

## Future scope

- True Gmail push notification architecture using Pub/Sub.
- Cloud Run deployment.
- Larger permission-safe datasets.
- More advanced report dashboard.
- Stronger evaluation metrics and CI coverage.
- Better error handling for Gmail/Drive quota, token expiry, and network failures.
