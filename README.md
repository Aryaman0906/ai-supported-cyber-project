# AI-Assisted Defensive Cybersecurity Mini-Project

Real-time phishing analysis and log triage project for defensive cybersecurity learning.

> **Responsible-use scope:** This project is defensive only. It is designed for sanitized datasets, sample emails, test URLs, sample logs, and user-provided input. It must not be used to generate phishing content, steal credentials, attack websites, scrape real inboxes without permission, or perform harmful activity.

## Phase 1: Setup

### Goal

Phase 1 creates the project foundation before any machine learning or API code is added. The goal is to separate future work into clear folders for:

1. Offline training scripts
2. Saved machine learning models
3. Real-time FastAPI prediction code
4. Optional monitoring code and sample data
5. Frontend demo files
6. Responsible-use and project documentation

This project will **not** stay notebook-only. Later phases will add trained models that are loaded once by FastAPI and used for instant predictions without retraining during requests.

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
├── requirements.txt
└── README.md
```

### What each folder is for

- `data/` stores sanitized learning data such as small CSV datasets, sample email text, test URLs, and local-only sample logs.
- `models/` stores trained model files saved with `joblib`, such as `text_phishing_model.joblib` and `url_phishing_model.joblib` in later phases.
- `train/` stores offline training scripts. Training happens here, not inside the API request path.
- `api/` stores FastAPI code and analyzer modules for real-time prediction endpoints.
- `frontend/` stores a simple browser-based demo page in a later phase.
- `report/` stores the responsible-use write-up and college submission explanation.
- `requirements.txt` lists the Python dependencies needed by the project.

`.gitkeep` files are empty placeholder files. Git does not track empty directories, so these files keep the planned folder structure visible until real files are added in later phases.

## Setup instructions

Run these commands from the repository root.

### 1. Confirm Python is installed

```bash
python --version
```

Recommended: Python 3.10 to 3.12 for the pinned beginner-friendly dependency set in this project.

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

## Common errors and fixes

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

If the error mentions Python version compatibility, confirm that you are using Python 3.10, 3.11, or 3.12 for this mini-project.

## Responsible-use notes for Phase 1

- No real inboxes, credentials, private logs, or production systems are used in this phase.
- Future sample data should be sanitized and safe for defensive learning.
- External threat-intelligence services, if added later, must use environment variables for API keys and should avoid sending private or sensitive data.

## What to do next

Continue to **Phase 2: Text/email phishing detection** after Phase 1 is working. Phase 2 will add a small `text,label` dataset, train a TF-IDF text classifier, evaluate it with multiple metrics, and save the model with `joblib`.

---

## Phase 2: Text/email phishing detection

### Goal

Phase 2 adds the first offline machine learning component: a small text/email phishing classifier. The important design rule is that **training and prediction stay separate**:

- Training happens offline in `train/train_text_model.py`.
- The trained model is saved to `models/text_phishing_model.joblib`.
- In Phase 3, FastAPI will load that saved model once at startup for real-time predictions.

This phase uses a beginner-friendly `TF-IDF + Logistic Regression` pipeline. TF-IDF converts email text into numeric features, and Logistic Regression learns a simple classifier from those features.

### Files added in Phase 2

- `data/phishing_dataset.csv` contains a small sanitized starter dataset with two columns: `text,label`.
- `train/train_text_model.py` loads the dataset, validates it, trains the text model, prints evaluation metrics, and saves the model.

### Dataset format

The CSV file must use this format:

```csv
text,label
"Team reminder: the security awareness session starts at 3 PM in room 204.",legitimate
"Urgent action required: confirm your login details to avoid permanent suspension.",phishing
```

Allowed labels are:

- `legitimate`
- `phishing`

The included starter dataset is intentionally small and sanitized. It is only for learning the workflow. A real project should later use a larger, permission-safe public dataset and carefully check for privacy, licensing, and bias concerns.

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

Accuracy can be misleading in cybersecurity datasets. For example, if 95% of emails are legitimate, a model that always predicts `legitimate` could appear to have high accuracy while missing dangerous phishing emails.

That is why this phase also reports:

- **Precision:** Of the messages predicted as phishing, how many were actually phishing?
- **Recall:** Of the actual phishing messages, how many did the model catch?
- **F1-score:** A balance between precision and recall.
- **Confusion matrix:** A table showing correct and incorrect predictions per class.

For defensive phishing detection, recall is especially important because missed phishing messages are risky. However, precision also matters because too many false alarms can cause alert fatigue.

### How to run Phase 2

First, activate your virtual environment and install dependencies if you have not already done so:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell, activate with:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Then run the training script from the repository root:

```bash
python -m train.train_text_model
```

Expected result:

- Evaluation metrics are printed in the terminal.
- A model file is created at `models/text_phishing_model.joblib`.

### How to test Phase 2

Check that the dataset file exists:

```bash
test -f data/phishing_dataset.csv
```

Check that the training script has valid Python syntax:

```bash
python -m py_compile train/train_text_model.py
```

Train the model:

```bash
python -m train.train_text_model
```

Check that the saved model file was created:

```bash
test -f models/text_phishing_model.joblib
```

### Common errors and fixes

#### `ModuleNotFoundError: No module named 'pandas'` or `No module named 'sklearn'`

Your dependencies are not installed in the active environment. Run:

```bash
pip install -r requirements.txt
```

Also confirm that your virtual environment is activated.

#### `Dataset not found`

Run the script from the repository root:

```bash
python -m train.train_text_model
```

The script expects the dataset at `data/phishing_dataset.csv`.

#### `Dataset is missing columns`

Make sure the CSV header is exactly:

```csv
text,label
```

#### Very high or very low metrics

The starter dataset is tiny, so metrics may change a lot when you edit examples. This is normal for a learning project. Later, improve the dataset size and quality before trusting the model.

### Responsible-use and limitation notes for Phase 2

- The included examples are sanitized and defensive.
- Do not train on private inboxes or real personal emails without permission.
- Do not include credentials, tokens, private links, or personal information in training data.
- This starter model is not production-grade and can produce false positives and false negatives.
- Human review is still required for real security decisions.

### What to do next

Continue to **Phase 3: Real-time FastAPI endpoint**. Phase 3 will load `models/text_phishing_model.joblib` once at API startup and expose `POST /analyze-text` for instant JSON predictions.

---

## Phase 3: Real-time FastAPI endpoint

### Goal

Phase 3 turns the Phase 2 text model into a real-time API feature. The important requirement is that the FastAPI server loads the trained model **once at startup** and then reuses it for every request.

This means:

- The API does **not** retrain the model during prediction.
- Users can paste sanitized email/text into an endpoint.
- The API immediately returns JSON with prediction, confidence, risk level, reasons, and a safety note.

### Files added in Phase 3

- `api/__init__.py` marks `api/` as a Python package.
- `api/text_analyzer.py` loads the saved text model and contains the reusable prediction logic.
- `api/main.py` creates the FastAPI app, loads the model during startup, exposes `/health`, and exposes `POST /analyze-text`.

### API behavior

#### `GET /health`

Use this endpoint to check whether the server is running and whether the text model loaded successfully.

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
  "detail": "Text model not found ... Run: python -m train.train_text_model"
}
```

#### `POST /analyze-text`

Request body:

```json
{
  "text": "Urgent action required: confirm your login details to avoid suspension."
}
```

Response body:

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

First, install dependencies and train the Phase 2 model:

```bash
pip install -r requirements.txt
python -m train.train_text_model
```

Then start the FastAPI server:

```bash
uvicorn api.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive Swagger UI will be available at:

```text
http://127.0.0.1:8000/docs
```

### How to test Phase 3

#### 1. Health check with curl

```bash
curl http://127.0.0.1:8000/health
```

#### 2. Analyze text with curl

```bash
curl -X POST http://127.0.0.1:8000/analyze-text \
  -H "Content-Type: application/json" \
  -d '{"text":"Urgent action required: confirm your login details to avoid suspension."}'
```

#### 3. Analyze text with Swagger UI

1. Open `http://127.0.0.1:8000/docs`.
2. Expand `POST /analyze-text`.
3. Click **Try it out**.
4. Paste a safe test message into the JSON body.
5. Click **Execute**.

#### 4. Analyze text with Postman

1. Set method to `POST`.
2. Set URL to `http://127.0.0.1:8000/analyze-text`.
3. Choose **Body → raw → JSON**.
4. Paste:

```json
{
  "text": "Please review the attached meeting agenda before Friday's project check-in."
}
```

5. Click **Send**.

### Common errors and fixes

#### `503 Service Unavailable` from `/analyze-text`

The API started, but the model file is missing. Run:

```bash
python -m train.train_text_model
```

Then restart Uvicorn.

#### `ModuleNotFoundError: No module named 'fastapi'`

Install dependencies inside your active virtual environment:

```bash
pip install -r requirements.txt
```

#### `Address already in use`

Another server is already running on port `8000`. Stop it or use a different port:

```bash
uvicorn api.main:app --reload --port 8001
```

#### Swagger UI opens, but prediction fails

Check `/health`. If `text_model_loaded` is `false`, train the model first and restart the API.

### Responsible-use and limitation notes for Phase 3

- Only paste sanitized or user-provided text that you have permission to analyze.
- Do not connect this endpoint to a real inbox yet.
- Do not send secrets, passwords, private links, or personal data to the API.
- The endpoint returns a model-assisted signal, not a final verdict.
- Human review is still required, especially for medium-risk or low-confidence results.

### What to do next

Continue to **Phase 4: URL phishing detection**. Phase 4 will add URL feature extraction, train a URL classifier, and expose `POST /analyze-url`.

---

## Phase 4: URL phishing detection

### Goal

Phase 4 adds URL phishing detection using explainable URL structure features. Like the text model, URL training is an offline step and real-time prediction happens through FastAPI.

This phase adds:

- A sanitized URL dataset.
- URL feature extraction.
- An offline Random Forest training script.
- A saved URL model at `models/url_phishing_model.joblib`.
- A real-time `POST /analyze-url` endpoint.

### Files added or updated in Phase 4

- `data/url_dataset.csv` contains safe sample URLs with `url,label` columns.
- `api/features.py` extracts URL features used by training and prediction.
- `train/train_url_model.py` trains and evaluates the URL classifier offline.
- `api/url_analyzer.py` loads the saved URL model and analyzes URLs in real time.
- `api/main.py` now loads both text and URL models at startup and exposes `POST /analyze-url`.

### URL features extracted

The URL analyzer extracts these features:

- `url_length`: total length of the URL.
- `uses_https`: whether the URL uses HTTPS.
- `has_ip_address`: whether the hostname is an IP address.
- `dot_count`: number of dots in the URL.
- `hyphen_count`: number of hyphens in the URL.
- `has_at_symbol`: whether the URL contains `@`.
- `suspicious_keyword_count`: count of common suspicious URL words such as `login`, `verify`, `password`, `urgent`, and `claim`.
- `subdomain_depth`: number of subdomain levels.
- `domain_length`: length of the registered domain string.
- `special_char_count`: number of non-alphanumeric characters.

These features are simple and explainable for learning. They are not enough for production-grade URL security by themselves.

### Dataset format

The URL CSV file must use this format:

```csv
url,label
https://www.university.edu/events/cybersecurity-workshop,legitimate
http://verify-account.example-risk.test/confirm,phishing
```

Allowed labels are:

- `legitimate`
- `phishing`

The sample suspicious URLs use documentation/test-style domains such as `example-risk.test` and reserved IP ranges where possible. Do not visit suspicious URLs during demos.

### How the URL training script works

`train/train_url_model.py` performs these steps:

1. Loads `data/url_dataset.csv`.
2. Checks that the required `url` and `label` columns exist.
3. Cleans blank rows and normalizes labels.
4. Extracts numeric URL features with `api/features.py`.
5. Splits the data into training and test sets.
6. Trains a `RandomForestClassifier` pipeline.
7. Prints accuracy, precision, recall, F1-score, a classification report, and a confusion matrix.
8. Saves the trained pipeline to `models/url_phishing_model.joblib`.

### How to run Phase 4

First install dependencies if needed:

```bash
pip install -r requirements.txt
```

Train the URL model:

```bash
python -m train.train_url_model
```

Start the API:

```bash
uvicorn api.main:app --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

### API behavior

#### `GET /health`

The health endpoint now reports both model states:

```json
{
  "status": "ok",
  "text_model_loaded": true,
  "url_model_loaded": true,
  "details": {
    "text_model": null,
    "url_model": null
  }
}
```

#### `POST /analyze-url`

Request body:

```json
{
  "url": "http://verify-account.example-risk.test/confirm"
}
```

Response body:

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

The exact score can vary when the dataset changes and the model is retrained.

### How to test Phase 4

Check that the URL dataset exists:

```bash
test -f data/url_dataset.csv
```

Check that URL-related Python files have valid syntax:

```bash
python -m py_compile api/features.py api/url_analyzer.py train/train_url_model.py api/main.py
```

Train the URL model:

```bash
python -m train.train_url_model
```

Check that the saved URL model exists:

```bash
test -f models/url_phishing_model.joblib
```

Start the API and test with curl:

```bash
curl -X POST http://127.0.0.1:8000/analyze-url \
  -H "Content-Type: application/json" \
  -d '{"url":"http://verify-account.example-risk.test/confirm"}'
```

### Common errors and fixes

#### `503 Service Unavailable` from `/analyze-url`

The API started, but the URL model file is missing. Run:

```bash
python -m train.train_url_model
```

Then restart Uvicorn.

#### `ModuleNotFoundError: No module named 'tldextract'`

Install dependencies inside your active virtual environment:

```bash
pip install -r requirements.txt
```

#### URL without `http://` or `https://`

The analyzer adds `http://` automatically when a scheme is missing. For clearer demos, include the full URL.

#### Model performs poorly

The starter dataset is tiny. Add more safe, permission-friendly labeled examples before drawing conclusions from the model.

### Responsible-use and limitation notes for Phase 4

- Do not visit suspicious URLs during testing.
- Do not submit private reset links, tokens, session URLs, or URLs containing personal information.
- The model uses simple structural features and may miss advanced phishing URLs.
- Legitimate URLs can contain suspicious-looking patterns, so false positives are possible.
- Treat the result as an assistive signal and combine it with human review.

### What to do next

Continue to **Phase 5: External threat intelligence checks**. Phase 5 will add optional PhishTank and VirusTotal support using environment variables for API keys while keeping the system usable without those keys.

---

## Phase 5: Optional external threat intelligence checks

### Goal

Phase 5 adds optional supporting checks from external threat-intelligence providers. These checks are **not required** for the project to work. The local ML/rule-based URL analysis still works without any API keys.

This phase adds optional checks for:

- VirusTotal URL reports.
- PhishTank URL lookups.

Important privacy rule: external checks can disclose the submitted URL to a third party. For that reason, the API only runs these checks when the request sets `include_external_checks` to `true`.

### Files added or updated in Phase 5

- `api/external_checks.py` contains optional VirusTotal and PhishTank lookup helpers.
- `api/url_analyzer.py` can include external-check results in URL analysis responses.
- `api/main.py` adds `include_external_checks` to the `/analyze-url` request body and returns an `external_checks` object.
- `.env.example` documents the optional environment variables without storing real keys.

### Environment variables

Do **not** hardcode API keys in Python files. Use environment variables instead.

Create a local `.env` file from the example file:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
VIRUSTOTAL_API_KEY=your_virustotal_key_here
PHISHTANK_API_KEY=your_phishtank_key_here
```

The `.env` file is ignored by Git. Keep real keys private.

If you do not provide keys, the API will return provider results with `status: "skipped"` instead of failing.

### How the checks work

#### VirusTotal

`api/external_checks.py` uses the VirusTotal API v3 URL report endpoint. It creates the VirusTotal URL identifier by URL-safe base64 encoding the submitted URL without padding, then requests a URL report using the `VIRUSTOTAL_API_KEY` header.

The response is summarized into:

- `malicious`
- `suspicious`
- `harmless`
- `undetected`
- `risk_hint`

#### PhishTank

`api/external_checks.py` sends a POST request to the PhishTank check URL endpoint when `PHISHTANK_API_KEY` is configured.

The response is summarized into:

- `in_database`
- `valid_phish`
- `verified`
- `risk_hint`

### Updated `/analyze-url` request

External checks are disabled by default:

```json
{
  "url": "http://verify-account.example-risk.test/confirm"
}
```

To opt in, set `include_external_checks` to `true`:

```json
{
  "url": "http://verify-account.example-risk.test/confirm",
  "include_external_checks": true
}
```

### Example response without external checks

```json
{
  "verdict": "phishing",
  "score": 0.91,
  "risk_level": "high",
  "extracted_features": {},
  "reasons": [],
  "external_checks": {
    "enabled": false,
    "privacy_note": "External checks were not requested. Set include_external_checks=true only for URLs you have permission to share with third-party services.",
    "providers": []
  },
  "safety_note": "Defensive URL analysis only. Do not visit suspicious URLs. Use this as a learning-project signal and verify manually."
}
```

### Example response with external checks but no API keys

```json
{
  "external_checks": {
    "enabled": true,
    "privacy_note": "The submitted URL may have been shared with configured third-party threat-intelligence providers. Do not submit private or sensitive URLs.",
    "providers": [
      {
        "provider": "virustotal",
        "status": "skipped",
        "reason": "VIRUSTOTAL_API_KEY is not set"
      },
      {
        "provider": "phishtank",
        "status": "skipped",
        "reason": "PHISHTANK_API_KEY is not set"
      }
    ]
  }
}
```

### How to run Phase 5

Install dependencies:

```bash
pip install -r requirements.txt
```

Optional: create `.env` and add keys:

```bash
cp .env.example .env
```

The application loads `.env` automatically with `python-dotenv`. You can also export variables in your shell instead.

Linux/macOS export example:

```bash
export VIRUSTOTAL_API_KEY="your_key_here"
export PHISHTANK_API_KEY="your_key_here"
```

Windows PowerShell export example:

```powershell
$env:VIRUSTOTAL_API_KEY="your_key_here"
$env:PHISHTANK_API_KEY="your_key_here"
```

Train the URL model if needed:

```bash
python -m train.train_url_model
```

Start the API:

```bash
uvicorn api.main:app --reload
```

Test with curl:

```bash
curl -X POST http://127.0.0.1:8000/analyze-url \
  -H "Content-Type: application/json" \
  -d '{"url":"http://verify-account.example-risk.test/confirm","include_external_checks":true}'
```

### Common errors and fixes

#### Provider returns `status: "skipped"`

The related API key is not set. This is expected when you have not configured optional external checks.

#### Provider returns `status: "error"` with rate limit text

You may have exceeded the provider's free-tier limit. Wait and try later, or disable external checks.

#### Request is slow

External services require network calls. The project uses short request timeouts, but external checks will still be slower than local ML prediction.

#### You are unsure whether a URL is private

Do not submit it to external checks. Keep `include_external_checks` as `false` and rely on local analysis plus human review.

### API limits and privacy concerns

- VirusTotal and PhishTank can have rate limits, quotas, authentication rules, and acceptable-use policies.
- API behavior can change over time, so check the official provider documentation before a final demo.
- Submitted URLs may be stored or shared by the provider.
- Never submit URLs containing credentials, password reset tokens, session IDs, private hostnames, or personal information.
- External results are supporting evidence only. They do not replace human review.

### What to do next

Continue to **Phase 6: Log triage module**. Phase 6 will add local sanitized log analysis and optional watchdog-based file monitoring.

---

## Phase 6: Log triage module and real-time monitoring

### Goal

Phase 6 adds defensive log triage for sanitized Apache/Nginx-style access logs. This gives the project its second real-time capability:

1. `POST /analyze-log-line` for instant API triage of one pasted log line.
2. `monitor_logs.py` for watchdog-based real-time monitoring of a local sample log file.

This module is local and defensive only. It does not attack, scan, exploit, or connect to any target system.

### Files added or updated in Phase 6

- `data/sample_logs.log` contains sanitized Apache/Nginx-style sample logs.
- `api/log_analyzer.py` parses log lines and detects suspicious local patterns.
- `api/main.py` exposes `POST /analyze-log-line`.
- `monitor_logs.py` watches a local sample log file with watchdog and prints alerts for suspicious new lines.

### Suspicious patterns detected

The Phase 6 rule-based analyzer checks for:

- Requests to sensitive or commonly probed paths such as `/admin`, `/wp-login`, `/.env`, `/backup`, `/config`, `/phpmyadmin`, and `/server-status`.
- Repeated `404` responses from the same IP during the current analyzer session.
- `401` or `403` authentication/authorization failure statuses.
- Requests for scanning-related file extensions such as `.zip`, `.bak`, `.sql`, `.env`, and `.old`.
- Many recent requests to many different paths from one IP.
- User-Agent values containing scanner/bot-like wording.

The analyzer returns:

- `verdict`: `normal`, `suspicious`, or `anomalous`.
- `risk_score`: integer from `0` to `100`.
- `risk_level`: `low`, `medium`, or `high`.
- `reasons`: human-readable explanation list.
- `parsed`: extracted log fields.
- `safety_note`: defensive-use reminder.

### Sample log format

The parser expects Apache/Nginx-style access log lines like:

```text
203.0.113.50 - - [13/Jun/2026:10:01:12 +0000] "GET /.env HTTP/1.1" 404 121 "-" "Scanner-Test-Agent"
```

### API usage: `POST /analyze-log-line`

Start the API:

```bash
uvicorn api.main:app --reload
```

Send a sanitized log line:

```bash
curl -X POST http://127.0.0.1:8000/analyze-log-line \
  -H "Content-Type: application/json" \
  -d '{"log_line":"203.0.113.50 - - [13/Jun/2026:10:01:12 +0000] \"GET /.env HTTP/1.1\" 404 121 \"-\" \"Scanner-Test-Agent\""}'
```

Example response:

```json
{
  "verdict": "anomalous",
  "risk_score": 75,
  "risk_level": "high",
  "reasons": [
    "Request targeted sensitive or commonly probed path(s): /.env.",
    "Request returned 404, which can indicate probing when repeated.",
    "Requested path ends with a file extension often targeted during scanning.",
    "User-Agent contains scanner/bot-like wording."
  ],
  "parsed": {
    "ip": "203.0.113.50",
    "timestamp": "13/Jun/2026:10:01:12 +0000",
    "method": "GET",
    "path": "/.env",
    "protocol": "HTTP/1.1",
    "status": 404,
    "size": "121",
    "referrer": "-",
    "user_agent": "Scanner-Test-Agent"
  },
  "safety_note": "Defensive local log triage only. Use sanitized logs and confirm alerts with human review before taking action."
}
```

### Real-time monitoring with watchdog

Install dependencies first:

```bash
pip install -r requirements.txt
```

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

The exact score may vary depending on previous lines analyzed in the current watcher session.

### How to test Phase 6

Check that the sample log file exists:

```bash
test -f data/sample_logs.log
```

Check syntax for the new files:

```bash
python -m py_compile api/log_analyzer.py api/main.py monitor_logs.py
```

Run a local analyzer smoke test without FastAPI:

```bash
python - <<'PY'
from api.log_analyzer import LogAnalyzer
line = '203.0.113.50 - - [13/Jun/2026:10:01:12 +0000] "GET /.env HTTP/1.1" 404 121 "-" "Scanner-Test-Agent"'
result = LogAnalyzer().analyze_line(line)
print(result.verdict, result.risk_score, result.risk_level)
PY
```

Start the API and test `/analyze-log-line` with curl as shown above.

Start `monitor_logs.py`, append a new sample line, and confirm that the watcher prints an `ALERT` for medium/high risk events.

### Optional advanced idea: IsolationForest

For a beginner mini-project, the rule-based analyzer is easier to explain and demo. An optional advanced extension is to train an `IsolationForest` on numeric log features such as status code, path length, request frequency, and unique path count. If you add this later, keep it offline/local and clearly explain false positives and false negatives.

### Common errors and fixes

#### `Log line does not match the expected Apache/Nginx-style format`

Make sure the line follows the sample format exactly, including quotes around the request, referrer, and User-Agent.

#### `ModuleNotFoundError: No module named 'watchdog'`

Install dependencies inside your active virtual environment:

```bash
pip install -r requirements.txt
```

#### Watcher starts but prints nothing

The watcher only analyzes lines appended after it starts. Open another terminal and append a new line to the watched file.

#### Too many alerts

The rules are intentionally simple and sensitive for learning. Tune thresholds in `api/log_analyzer.py` after testing with more sanitized logs.

### Responsible-use and limitation notes for Phase 6

- Use only sanitized logs, toy logs, or logs you have explicit permission to analyze.
- Do not monitor production systems for this college mini-project unless your institution explicitly authorizes it.
- Do not store credentials, tokens, private IP mappings, or personal data in sample logs.
- Rule-based detection can create false positives and false negatives.
- Alerts should be reviewed by a human before taking action.

### What to do next

Continue to **Phase 7: Simple frontend**. Phase 7 will add a browser page that can call the text, URL, and log analysis endpoints.

---

## Phase 7: Simple frontend

### Goal

Phase 7 adds a beginner-friendly browser page for the real-time API. The frontend lets a user paste:

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

First install dependencies and train the models if you have not already done so:

```bash
pip install -r requirements.txt
python -m train.train_text_model
python -m train.train_url_model
```

Start FastAPI:

```bash
uvicorn api.main:app --reload
```

Then open the frontend file in your browser:

```text
frontend/index.html
```

You can usually open it by double-clicking the file, or by right-clicking and choosing **Open With → Browser**.

Optional: serve the frontend with Python's built-in static file server:

```bash
python -m http.server 8080 --directory frontend
```

Then open:

```text
http://127.0.0.1:8080
```

### How to test Phase 7

Check that the frontend file exists:

```bash
test -f frontend/index.html
```

Check that the frontend references the expected API endpoints:

```bash
python - <<'PY'
from pathlib import Path
html = Path('frontend/index.html').read_text()
required = ['/health', '/analyze-text', '/analyze-url', '/analyze-log-line']
missing = [item for item in required if item not in html]
if missing:
    raise SystemExit(f'Missing expected endpoint strings: {missing}')
print('frontend endpoint references OK')
PY
```

Manual browser test:

1. Start FastAPI with `uvicorn api.main:app --reload`.
2. Open `frontend/index.html` in a browser.
3. Click **Check API health**.
4. Test the sample text, URL, and log line already filled into the page.
5. Confirm each result shows a verdict, score/confidence, risk badge, reasons, and raw JSON.

### Common errors and fixes

#### Browser shows `Failed to fetch`

FastAPI is probably not running, or the base URL is wrong. Start the backend:

```bash
uvicorn api.main:app --reload
```

Then confirm the page's API base URL is:

```text
http://127.0.0.1:8000
```

#### `/analyze-text` or `/analyze-url` returns `503 Service Unavailable`

The related model file has not been trained yet. Run:

```bash
python -m train.train_text_model
python -m train.train_url_model
```

Then restart FastAPI.

#### URL external checks return `skipped`

This is normal if API keys are not configured. External checks are optional.

#### Log analysis says the format is invalid

Use the sample log format from `data/sample_logs.log`. The parser expects quotes around the request, referrer, and User-Agent fields.

### Responsible-use and limitation notes for Phase 7

- Do not paste real credentials, private URLs, private emails, or sensitive logs into the demo.
- The frontend is a local educational demo, not a hardened production application.
- External checks can disclose URLs to third-party providers when enabled.
- Model and rule outputs are assistive signals only and need human review.
- CORS is permissive for local learning; restrict it before any real deployment.

### What to do next

Continue to **Phase 8: Report and documentation**. Phase 8 will add the responsible-use write-up and a college-submission-style project explanation.

---

## Phase 8: Report and documentation

### Goal

Phase 8 completes the college-submission documentation. The goal is to clearly explain what the project does, how it works, how to demo it, what its limitations are, and how it must be used responsibly.

### Files added in Phase 8

- `report/responsible_use.md` explains defensive purpose, prohibited uses, privacy, false positives, false negatives, dataset bias, adversarial evasion, human review, and safe deployment.
- `report/project_explanation.md` provides a college-submission-style explanation with abstract, problem statement, objectives, architecture, methods, run steps, expected outputs, limitations, and future improvements.

### Final demo checklist

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
13. Explain the responsible-use notes and limitations.

### Suggested college presentation flow

1. **Problem:** phishing and suspicious logs are common defensive security problems.
2. **Design:** training is offline, prediction is real time, monitoring is local.
3. **Text model:** TF-IDF + Logistic Regression.
4. **URL model:** explainable URL features + Random Forest.
5. **API:** FastAPI endpoints return JSON instantly.
6. **Monitoring:** watchdog observes a sample log file.
7. **Frontend:** browser page calls the API.
8. **Responsible use:** no offensive activity, no private data, human review required.
9. **Limitations:** small datasets, false positives, false negatives, adversarial evasion.
10. **Future work:** larger datasets, better tests, safe test inbox integration, optional anomaly models.

### How to test Phase 8

Check that the report files exist:

```bash
test -f report/responsible_use.md && test -f report/project_explanation.md
```

Check that the report files are not empty:

```bash
python - <<'PY'
from pathlib import Path
for path in [Path('report/responsible_use.md'), Path('report/project_explanation.md')]:
    text = path.read_text().strip()
    if not text:
        raise SystemExit(f'{path} is empty')
    print(f'{path}: {len(text.split())} words')
PY
```

### Common errors and fixes

#### Report is too long for submission

Use `report/project_explanation.md` as the detailed version, then create a shorter summary from it if your college has a page limit.

#### Teacher asks about safety

Use `report/responsible_use.md` to explain the defensive-only scope, privacy protections, false positives, false negatives, and human review requirement.

#### Demo model results look imperfect

Explain that the starter datasets are small and the project is focused on architecture and responsible real-time workflow, not production-level detection accuracy.

### Final responsible-use reminder

This project is for defensive learning only. Do not use it for phishing generation, credential theft, unauthorized monitoring, scanning, exploitation, or analysis of private data without permission.

---

## Final validation and real-time readiness check

After Phase 8, run this dependency-light checker first:

```bash
python tests/phase_completion_check.py
```

This script verifies that:

- All expected project files exist.
- The text and URL datasets use the required CSV headers.
- FastAPI endpoint strings are present in `api/main.py`.
- The frontend references `/health`, `/analyze-text`, `/analyze-url`, and `/analyze-log-line`.
- The report files contain the required responsible-use and project-explanation sections.
- The local log analyzer can parse and score a suspicious sanitized log line.

To fully verify real-time ML/API behavior, install dependencies, train both models, start FastAPI, and test the endpoints:

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

If dependency installation is blocked by your environment or network, the dependency-light checker still confirms the repository structure and local log analyzer behavior. Full model training and FastAPI runtime tests require the packages in `requirements.txt`.
