# AI-Assisted Defensive Cybersecurity Mini-Project

Near-real-time phishing analysis, URL checking, log triage, and scheduled Gmail report generation project for defensive cybersecurity learning.

> **Responsible-use scope:** This project is defensive only. It is designed for sanitized datasets, sample emails, test URLs, sample logs, and user-authorized Gmail analysis. It must not be used to generate phishing content, steal credentials, attack websites, scrape inboxes without permission, or perform harmful activity.

## Current final implementation

The current working flow is a **local scheduled automation system**, not a full cloud-native Gmail push-monitoring system.

```text
Windows Task Scheduler
        ↓
Local Gmail polling / scan script
        ↓
AI-assisted email, URL, and log analysis
        ↓
Report generation: CSV + Markdown + Excel
        ↓
Automatic upload to configured Google Drive folder
```

### Correct architecture claim

This project uses **near-real-time Gmail polling using Windows Task Scheduler**. The scheduler periodically runs the local scan/report script. After the scan finishes, the system generates reports in `.csv`, `.md`, and `.xlsx` formats and uploads them to Google Drive.

The current implementation does **not** use Gmail push notifications for instant processing, Google Pub/Sub, or Cloud Run. Those can be treated as future optional improvements.

### Current status summary

| Component | Status |
|---|---|
| Text/email phishing classifier | Implemented |
| URL phishing classifier | Implemented |
| FastAPI prediction endpoints | Implemented |
| Local frontend demo | Implemented |
| Local log triage | Implemented |
| Gmail polling through local script | Implemented |
| Windows Task Scheduler automation | Implemented locally |
| CSV report generation | Implemented |
| Markdown report generation | Implemented |
| Excel report generation | Implemented |
| Google Drive report upload | Implemented locally |
| Gmail push-based instant processing | Not implemented; future scope only |
| Cloud Run / Pub/Sub deployment | Not current architecture; future optional only |

## Safety and privacy notes

- Analyze only emails, logs, and URLs that you own or have explicit permission to process.
- Do not commit `credentials.json`, `token.json`, `.env`, generated reports containing private email data, logs, or API keys to Git.
- Use sample or redacted report files in GitHub and college submissions.
- Model predictions are assistive signals only. Human review is still required.
- External threat-intelligence checks can disclose submitted URLs to third-party providers, so they are optional and disabled unless requested.

Recommended `.gitignore` entries:

```gitignore
.venv/
__pycache__/
*.pyc
.env
credentials.json
token.json
task-log.txt
logs/
reports/generated/
reports/private/
*.secret
```

## Phase 1: Setup

### Goal

Phase 1 creates the project foundation before machine learning, API, Gmail, Drive, or scheduler code is added. The goal is to separate future work into clear folders for:

1. Offline training scripts
2. Saved machine learning models
3. FastAPI prediction code for instant local API responses
4. Local log monitoring and scheduled Gmail polling code
5. Report generation and Google Drive upload workflow
6. Frontend demo files
7. Responsible-use and project documentation

Training and prediction stay separate. Trained models are saved once and then loaded by FastAPI or local scripts for prediction.

## Project structure

```text
ai-supported-cyber-project/
├── data/
│   └── .gitkeep
├── models/
│   └── .gitkeep
├── train/
│   └── .gitkeep
├── api/
│   └── .gitkeep
├── frontend/
│   └── .gitkeep
├── report/
│   └── .gitkeep
├── reports/
│   ├── generated/
│   └── .gitkeep
├── scheduler/
│   └── .gitkeep
├── requirements.txt
├── .gitignore
└── README.md
```

### What each folder is for

- `data/` stores sanitized learning data such as small CSV datasets, sample email text, test URLs, and local-only sample logs.
- `models/` stores trained model files saved with `joblib`, such as `text_phishing_model.joblib` and `url_phishing_model.joblib`.
- `train/` stores offline training scripts. Training happens here, not inside the API request path.
- `api/` stores FastAPI code and analyzer modules for instant local prediction endpoints.
- `frontend/` stores the browser-based demo page.
- `report/` stores responsible-use documentation and the college submission explanation.
- `reports/generated/` stores locally generated CSV, Markdown, and Excel reports before or after upload.
- `scheduler/` stores local automation scripts, batch files, or Task Scheduler notes if used in your repository.
- `requirements.txt` lists the Python dependencies needed by the project.

`.gitkeep` files are empty placeholder files. Git does not track empty directories, so these files keep the planned folder structure visible until real files are added.

## Setup instructions

Run these commands from the repository root.

### 1. Confirm Python is installed

```bash
python --version
```

Recommended: Python 3.10 to 3.12.

If your system uses `python3` instead of `python`, use `python3` in the commands below.

### 2. Create a virtual environment

Linux/macOS:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
python -m venv .venv
```

### 3. Activate the virtual environment

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

After activation, your terminal prompt should usually show `(.venv)`.

### 4. Upgrade pip

```bash
python -m pip install --upgrade pip
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

## How to test Phase 1

### Check that dependencies can be installed

```bash
pip install -r requirements.txt
```

### Check that important packages import correctly

```bash
python -c "import fastapi, sklearn, pandas, joblib, watchdog, tldextract; print('Phase 1 imports OK')"
```

Expected output:

```text
Phase 1 imports OK
```

## Common setup errors and fixes

### `python: command not found`

Try:

```bash
python3 --version
python3 -m venv .venv
```

### Virtual environment activation is blocked on Windows

In PowerShell, you may need to run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Package installation fails

Try upgrading pip first:

```bash
python -m pip install --upgrade pip
```

If the error mentions Python version compatibility, confirm that you are using Python 3.10, 3.11, or 3.12.

## Responsible-use notes for Phase 1

- No private inboxes, credentials, private logs, or production systems should be used without permission.
- Future sample data should be sanitized and safe for defensive learning.
- External threat-intelligence services, if added, must use environment variables for API keys and should avoid sending private or sensitive data.

## Phase 2: Text/email phishing detection

### Goal

Phase 2 adds the first offline machine learning component: a small text/email phishing classifier. Training and prediction stay separate:

- Training happens offline in `train/train_text_model.py`.
- The trained model is saved to `models/text_phishing_model.joblib`.
- FastAPI or local automation scripts load that saved model for predictions.

This phase uses a beginner-friendly `TF-IDF + Logistic Regression` pipeline.

### Files added in Phase 2

- `data/phishing_dataset.csv` contains a small sanitized starter dataset with two columns: `text,label`.
- `train/train_text_model.py` loads the dataset, validates it, trains the text model, prints evaluation metrics, and saves the model.

### Dataset format

```csv
text,label
"Team reminder: the security awareness session starts at 3 PM in room 204.",legitimate
"Urgent action required: confirm your login details to avoid permanent suspension.",phishing
```

Allowed labels:

- `legitimate`
- `phishing`

The included starter dataset is intentionally small and sanitized. It is only for learning the workflow. A real project should later use a larger, permission-safe public dataset and check privacy, licensing, and bias concerns.

### How the training script works

`train/train_text_model.py` performs these steps:

1. Loads `data/phishing_dataset.csv`.
2. Checks that the required `text` and `label` columns exist.
3. Cleans blank rows and normalizes labels.
4. Splits the data into training and test sets.
5. Builds a scikit-learn pipeline:
   - `TfidfVectorizer` for text features.
   - `LogisticRegression` for classification.
6. Prints accuracy, precision, recall, F1-score, a classification report, and a confusion matrix.
7. Saves the trained pipeline to `models/text_phishing_model.joblib`.

### Why accuracy alone is not enough

Accuracy can be misleading in cybersecurity datasets. If 95% of emails are legitimate, a model that always predicts `legitimate` could appear accurate while missing dangerous phishing emails.

That is why this phase also reports:

- **Precision:** Of the messages predicted as phishing, how many were actually phishing?
- **Recall:** Of the actual phishing messages, how many did the model catch?
- **F1-score:** A balance between precision and recall.
- **Confusion matrix:** A table showing correct and incorrect predictions per class.

For defensive phishing detection, recall is important because missed phishing messages are risky. Precision also matters because too many false alarms can cause alert fatigue.

### How to run Phase 2

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m train.train_text_model
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m train.train_text_model
```

Expected result:

- Evaluation metrics are printed in the terminal.
- A model file is created at `models/text_phishing_model.joblib`.

### How to test Phase 2

```bash
python -m py_compile train/train_text_model.py
python -m train.train_text_model
```

Then confirm that this file exists:

```text
models/text_phishing_model.joblib
```

## Phase 3: FastAPI endpoint for instant text prediction

### Goal

Phase 3 turns the Phase 2 text model into an API feature. FastAPI loads the trained model once at startup and reuses it for requests.

This means:

- The API does not retrain the model during prediction.
- Users can paste sanitized email/text into an endpoint.
- The API returns JSON with prediction, confidence, risk level, reasons, and a safety note.

### Files added in Phase 3

- `api/__init__.py` marks `api/` as a Python package.
- `api/text_analyzer.py` loads the saved text model and contains reusable prediction logic.
- `api/main.py` creates the FastAPI app, loads the model during startup, exposes `/health`, and exposes `POST /analyze-text`.

### API behavior

#### `GET /health`

Example response when the model is loaded:

```json
{
  "status": "ok",
  "text_model_loaded": true,
  "detail": null
}
```

Example response when the model has not been trained yet:

```json
{
  "status": "model_not_loaded",
  "text_model_loaded": false,
  "detail": "Text model not found. Run: python -m train.train_text_model"
}
```

#### `POST /analyze-text`

Request body:

```json
{
  "text": "Urgent action required: confirm your login details to avoid suspension."
}
```

Example response:

```json
{
  "prediction": "phishing",
  "confidence": 0.83,
  "risk_level": "high",
  "reasons": [
    "The offline-trained text model predicted 'phishing' with confidence 0.83.",
    "The text contains common phishing-pressure or credential-related wording: urgent, login."
  ],
  "safety_note": "Defensive analysis only. This result is a learning-project signal, not a final security decision. Review suspicious messages manually."
}
```

The exact confidence and prediction can vary when the dataset changes and the model is retrained.

### How to run Phase 3

```bash
pip install -r requirements.txt
python -m train.train_text_model
uvicorn api.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

### How to test Phase 3

```bash
curl http://127.0.0.1:8000/health
```

```bash
curl -X POST http://127.0.0.1:8000/analyze-text \
  -H "Content-Type: application/json" \
  -d '{"text":"Urgent action required: confirm your login details to avoid suspension."}'
```

## Phase 4: URL phishing detection

### Goal

Phase 4 adds URL phishing detection using explainable URL structure features. Like the text model, URL training is an offline step and prediction happens through FastAPI or local automation.

This phase adds:

- A sanitized URL dataset.
- URL feature extraction.
- An offline Random Forest training script.
- A saved URL model at `models/url_phishing_model.joblib`.
- A `POST /analyze-url` endpoint.

### Files added or updated in Phase 4

- `data/url_dataset.csv` contains safe sample URLs with `url,label` columns.
- `api/features.py` extracts URL features used by training and prediction.
- `train/train_url_model.py` trains and evaluates the URL classifier offline.
- `api/url_analyzer.py` loads the saved URL model and analyzes URLs.
- `api/main.py` loads both text and URL models at startup and exposes `POST /analyze-url`.

### URL features extracted

The URL analyzer extracts these features:

- `url_length`
- `uses_https`
- `has_ip_address`
- `dot_count`
- `hyphen_count`
- `has_at_symbol`
- `suspicious_keyword_count`
- `subdomain_depth`
- `domain_length`
- `special_char_count`

These features are simple and explainable for learning. They are not enough for production-grade URL security by themselves.

### Dataset format

```csv
url,label
https://www.university.edu/events/cybersecurity-workshop,legitimate
http://verify-account.example-risk.test/confirm,phishing
```

Allowed labels:

- `legitimate`
- `phishing`

The sample suspicious URLs use documentation/test-style domains where possible. Do not visit suspicious URLs during demos.

### How to run Phase 4

```bash
pip install -r requirements.txt
python -m train.train_url_model
uvicorn api.main:app --reload
```

### API behavior

#### `POST /analyze-url`

Request body:

```json
{
  "url": "http://verify-account.example-risk.test/confirm"
}
```

Example response:

```json
{
  "verdict": "phishing",
  "score": 0.91,
  "risk_level": "high",
  "extracted_features": {
    "url_length": 47,
    "uses_https": 0,
    "has_ip_address": 0,
    "dot_count": 2,
    "hyphen_count": 2,
    "has_at_symbol": 0,
    "suspicious_keyword_count": 3,
    "subdomain_depth": 0,
    "domain_length": 17,
    "special_char_count": 8
  },
  "reasons": [
    "The offline-trained URL model predicted 'phishing' with score 0.91.",
    "The URL does not use HTTPS.",
    "The URL contains suspicious keywords often seen in credential or urgency lures."
  ],
  "safety_note": "Defensive URL analysis only. Do not visit suspicious URLs. Use this as a learning-project signal and verify manually."
}
```

### How to test Phase 4

```bash
python -m py_compile api/features.py api/url_analyzer.py train/train_url_model.py api/main.py
python -m train.train_url_model
```

Then test with curl:

```bash
curl -X POST http://127.0.0.1:8000/analyze-url \
  -H "Content-Type: application/json" \
  -d '{"url":"http://verify-account.example-risk.test/confirm"}'
```

## Phase 5: Optional external threat intelligence checks

### Goal

Phase 5 adds optional supporting checks from external threat-intelligence providers. These checks are not required for the project to work. The local ML/rule-based URL analysis still works without API keys.

This phase adds optional checks for:

- VirusTotal URL reports.
- PhishTank URL lookups.

Important privacy rule: external checks can disclose the submitted URL to a third party. For that reason, the API only runs these checks when the request sets `include_external_checks` to `true`.

### Files added or updated in Phase 5

- `api/external_checks.py` contains optional VirusTotal and PhishTank lookup helpers.
- `api/url_analyzer.py` can include external-check results in URL analysis responses.
- `api/main.py` adds `include_external_checks` to the `/analyze-url` request body.
- `.env.example` documents optional environment variables without storing real keys.

### Environment variables

Do not hardcode API keys in Python files. Use environment variables instead.

```bash
cp .env.example .env
```

Example `.env`:

```env
VIRUSTOTAL_API_KEY=your_virustotal_key_here
PHISHTANK_API_KEY=your_phishtank_key_here
```

The `.env` file is ignored by Git. Keep real keys private.

### Updated `/analyze-url` request

External checks are disabled by default:

```json
{
  "url": "http://verify-account.example-risk.test/confirm"
}
```

To opt in:

```json
{
  "url": "http://verify-account.example-risk.test/confirm",
  "include_external_checks": true
}
```

### API limits and privacy concerns

- VirusTotal and PhishTank can have rate limits, quotas, authentication rules, and acceptable-use policies.
- Submitted URLs may be stored or shared by the provider.
- Never submit URLs containing credentials, password reset tokens, session IDs, private hostnames, or personal information.
- External results are supporting evidence only. They do not replace human review.

## Phase 6: Log triage module and local file monitoring

### Goal

Phase 6 adds defensive log triage for sanitized Apache/Nginx-style access logs. This gives the project local monitoring and triage capabilities:

1. `POST /analyze-log-line` for API triage of one pasted log line.
2. `monitor_logs.py` for watchdog-based monitoring of a local sample log file.

This module is local and defensive only. It does not attack, scan, exploit, or connect to any target system.

### Files added or updated in Phase 6

- `data/sample_logs.log` contains sanitized Apache/Nginx-style sample logs.
- `api/log_analyzer.py` parses log lines and detects suspicious local patterns.
- `api/main.py` exposes `POST /analyze-log-line`.
- `monitor_logs.py` watches a local sample log file with watchdog and prints alerts for suspicious new lines.

### Suspicious patterns detected

The analyzer checks for:

- Requests to sensitive or commonly probed paths such as `/admin`, `/wp-login`, `/.env`, `/backup`, `/config`, `/phpmyadmin`, and `/server-status`.
- Repeated `404` responses from the same IP during the current analyzer session.
- `401` or `403` authentication/authorization failure statuses.
- Requests for scanning-related file extensions such as `.zip`, `.bak`, `.sql`, `.env`, and `.old`.
- Many recent requests to many different paths from one IP.
- User-Agent values containing scanner/bot-like wording.

### Sample log format

```text
203.0.113.50 - - [13/Jun/2026:10:01:12 +0000] "GET /.env HTTP/1.1" 404 121 "-" "Scanner-Test-Agent"
```

### API usage: `POST /analyze-log-line`

```bash
curl -X POST http://127.0.0.1:8000/analyze-log-line \
  -H "Content-Type: application/json" \
  -d '{"log_line":"203.0.113.50 - - [13/Jun/2026:10:01:12 +0000] \"GET /.env HTTP/1.1\" 404 121 \"-\" \"Scanner-Test-Agent\""}'
```

### Local file monitoring with watchdog

Start the watcher:

```bash
python monitor_logs.py --file data/sample_logs.log
```

Open another terminal and append a safe sample suspicious log line:

```bash
printf '%s\n' '203.0.113.50 - - [13/Jun/2026:10:05:00 +0000] "GET /admin HTTP/1.1" 403 300 "-" "Scanner-Test-Agent"' >> data/sample_logs.log
```

Expected watcher output:

```text
ALERT risk=medium verdict=suspicious score=60 ip=203.0.113.50 path=/admin reasons=...
```

## Phase 7: Simple frontend

### Goal

Phase 7 adds a browser page for the local API. The frontend lets a user paste:

1. Email/text content.
2. A URL.
3. One sanitized log line.

The page calls the FastAPI endpoints with `fetch()` and displays the verdict, score/confidence, risk level, reasons, and raw JSON response.

### File added in Phase 7

- `frontend/index.html` is a single-file HTML/CSS/JavaScript demo page.

### What the frontend can do

The page includes:

- A FastAPI base URL setting, defaulting to `http://127.0.0.1:8000`.
- A **Check API health** button that calls `GET /health`.
- An **Email/Text analysis** card that calls `POST /analyze-text`.
- A **URL analysis** card that calls `POST /analyze-url`.
- An optional checkbox for `include_external_checks`.
- A **Log line triage** card that calls `POST /analyze-log-line`.
- Result cards with risk badges, reasons, and expandable raw JSON.

### How to run Phase 7

```bash
pip install -r requirements.txt
python -m train.train_text_model
python -m train.train_url_model
uvicorn api.main:app --reload
```

Then open:

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

## Phase 8: Report and documentation

### Goal

Phase 8 completes the college-submission documentation. The goal is to clearly explain what the project does, how it works, how to demo it, what its limitations are, and how it must be used responsibly.

### Files added in Phase 8

- `report/responsible_use.md` explains defensive purpose, prohibited uses, privacy, false positives, false negatives, dataset bias, adversarial evasion, human review, and safe deployment.
- `report/project_explanation.md` provides a college-submission-style explanation with abstract, problem statement, objectives, architecture, methods, run steps, expected outputs, limitations, and future improvements.

### Suggested college presentation flow

1. **Problem:** phishing emails, suspicious URLs, and suspicious logs are common defensive security problems.
2. **Design:** training is offline, API prediction is instant, Gmail scanning is scheduled local polling, and reports are uploaded to Google Drive.
3. **Text model:** TF-IDF + Logistic Regression.
4. **URL model:** explainable URL features + Random Forest.
5. **API:** FastAPI endpoints return JSON predictions.
6. **Monitoring:** watchdog observes a local sample log file.
7. **Gmail automation:** Windows Task Scheduler periodically runs the Gmail scan/report workflow.
8. **Reports:** CSV, Markdown, and Excel reports are generated and uploaded to Google Drive.
9. **Responsible use:** no offensive activity, no private data in Git, human review required.
10. **Limitations:** small datasets, false positives, false negatives, adversarial evasion, and polling delay.
11. **Future work:** larger datasets, better tests, safe dashboard report viewing, GitHub Actions CI, optional Cloud Run/Pub/Sub architecture.

## Phase 9: Scheduled Gmail polling and Google Drive reports

### Goal

Phase 9 adds the finalized report automation flow. The system periodically checks Gmail using a local scheduled script, analyzes authorized email data, generates reports, and uploads those reports to Google Drive.

This phase is **near-real-time polling**, not Gmail push-based instant processing.

### Final automation flow

```text
Task Scheduler trigger
        ↓
Run local batch/script file
        ↓
Authenticate with Gmail API using local OAuth token
        ↓
Fetch new or relevant emails through polling
        ↓
Analyze email text and URLs
        ↓
Apply labels or classification results where configured
        ↓
Generate reports locally
        ↓
Upload CSV, Markdown, and Excel reports to Google Drive
        ↓
Write success/error details to task log
```

### Report outputs

The scheduled workflow generates these report formats:

| Format | Purpose |
|---|---|
| `.csv` | Simple tabular result export |
| `.md` | Readable Markdown summary for documentation |
| `.xlsx` | Excel report for filtering, sorting, and presentation |

Reports are generated locally first and then uploaded to the configured Google Drive folder.

### Task Scheduler behavior

Windows Task Scheduler is used to run the local scan/report script at a configured interval. Example intervals may be every 5, 10, 15, or 30 minutes depending on demo requirements.

This means Gmail is checked periodically. There can be a delay between when an email arrives and when the next scheduled scan processes it.

### Proof to include in GitHub or project report

Add screenshots or redacted proof for:

1. Task Scheduler task list showing the project task.
2. Task Scheduler trigger settings.
3. Task Scheduler action pointing to the batch/script file.
4. Local reports folder showing generated `.csv`, `.md`, and `.xlsx` files.
5. Google Drive folder showing uploaded reports.
6. `task-log.txt` or terminal output showing a successful scheduled run.
7. Redacted Gmail label/classification proof if the workflow applies Gmail labels.

Do not upload screenshots that reveal personal emails, OAuth tokens, private Drive links, or secret file paths.

### Common Gmail/Drive automation errors and fixes

#### OAuth token expires or becomes invalid

Re-run the Gmail/Drive authentication setup locally and regenerate the token. Do not commit the token to Git.

#### Reports generate locally but do not appear in Google Drive

Check:

- Drive API credentials are valid.
- The target Drive folder ID is correct.
- The upload function is called after report generation.
- The scheduled task is running from the correct project directory.
- The task log contains no permission or file-path errors.

#### Task Scheduler shows success but no report is generated

Check:

- The task action uses the correct `.bat` file or Python command.
- The task starts in the repository root directory.
- The virtual environment path is correct.
- File paths are absolute or correctly resolved.
- `task-log.txt` captures both standard output and errors.

#### Same emails are scanned repeatedly

Use duplicate-scan prevention through message IDs, local state files, or a database. Document which method your project uses.

#### Two scans overlap

Add a lock file or process guard so a new scheduled run does not start if the previous scan is still running.

### Correct wording for report/demo

Use:

> The project uses near-real-time Gmail polling through Windows Task Scheduler. The local scheduler runs the scan/report script at configured intervals, generates CSV, Markdown, and Excel reports, and uploads those reports to Google Drive.

Avoid:

> The project monitors Gmail in full real time.

Avoid:

> The project is fully cloud-native.

## Final demo checklist

Use this checklist before presenting:

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Train the text model with `python -m train.train_text_model`.
4. Train the URL model with `python -m train.train_url_model`.
5. Start FastAPI with `uvicorn api.main:app --reload`.
6. Open Swagger UI at `http://127.0.0.1:8000/docs`.
7. Test `POST /analyze-text`.
8. Test `POST /analyze-url`.
9. Test `POST /analyze-log-line`.
10. Open `frontend/index.html` and test all three cards.
11. Start `monitor_logs.py --file data/sample_logs.log`.
12. Append a safe sample log line and confirm an alert appears.
13. Run the Gmail scan/report script manually once.
14. Confirm CSV, Markdown, and Excel reports are generated locally.
15. Confirm the same reports are uploaded to Google Drive.
16. Run or wait for the Windows Task Scheduler job.
17. Confirm the scheduled run writes success details to `task-log.txt`.
18. Explain that Gmail scanning is scheduled polling, not push-based instant processing.
19. Explain responsible-use limits and privacy protections.

## Final validation and readiness check

After documentation is complete, run this dependency-light checker first if available:

```bash
python tests/phase_completion_check.py
```

This script should verify that:

- Expected project files exist.
- The text and URL datasets use the required CSV headers.
- FastAPI endpoint strings are present in `api/main.py`.
- The frontend references `/health`, `/analyze-text`, `/analyze-url`, and `/analyze-log-line`.
- The report files contain the required responsible-use and project-explanation sections.
- The local log analyzer can parse and score a suspicious sanitized log line.

To fully verify ML/API behavior:

```bash
pip install -r requirements.txt
python -m train.train_text_model
python -m train.train_url_model
uvicorn api.main:app --reload
```

Then test in another terminal:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/analyze-text -H "Content-Type: application/json" -d '{"text":"Urgent action required: confirm your login details."}'
curl -X POST http://127.0.0.1:8000/analyze-url -H "Content-Type: application/json" -d '{"url":"http://verify-account.example-risk.test/confirm"}'
curl -X POST http://127.0.0.1:8000/analyze-log-line -H "Content-Type: application/json" -d '{"log_line":"203.0.113.50 - - [13/Jun/2026:10:01:12 +0000] \"GET /.env HTTP/1.1\" 404 121 \"-\" \"Scanner-Test-Agent\""}'
```

To verify scheduled Gmail/Drive automation:

```text
1. Run the local Gmail scan/report script manually.
2. Confirm generated CSV, Markdown, and Excel reports.
3. Confirm Google Drive upload.
4. Trigger the Task Scheduler job manually.
5. Confirm the same report flow works from Task Scheduler.
6. Check task-log.txt for success or error output.
```

## Future optional improvements

These are not part of the current working architecture unless implemented and proven:

- Google Cloud Run deployment.
- Gmail push notifications through Google Pub/Sub.
- GitHub Actions CI.
- Dashboard endpoint to view or download generated reports.
- Stronger HTML email parsing.
- Task overlap protection through lock files.
- Larger public datasets and stronger model evaluation.
- Better dashboard with charts and filters.

## Final responsible-use reminder

This project is for defensive learning only. Do not use it for phishing generation, credential theft, unauthorized monitoring, scanning, exploitation, or analysis of private data without permission.
