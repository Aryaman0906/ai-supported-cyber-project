# Project Explanation for College Submission

## Title

**AI-Assisted Defensive Cybersecurity Mini-Project: Real-Time Phishing Analysis and Log Triage with Responsible-Use Write-Up**

## Abstract

This project is a defensive cybersecurity mini-project that demonstrates how machine learning and rule-based analysis can support phishing detection and log triage in real time. The project separates offline model training from real-time prediction. Text and URL models are trained in separate scripts, saved with `joblib`, and loaded once by a FastAPI server. The API provides endpoints for analyzing email/text, URLs, and sanitized web server log lines. A simple frontend allows users to paste safe examples and view predictions, confidence/risk scores, explanations, and raw JSON results.

The project also includes optional external URL reputation checks through VirusTotal and PhishTank, but these checks are disabled by default for privacy. A watchdog-based log monitor demonstrates real-time monitoring by watching a local sample log file and printing alerts when suspicious lines are appended.

## Problem statement

Phishing messages, deceptive URLs, and suspicious web requests are common security problems. Beginners often study phishing detection only in notebooks, which does not show how a real system would respond to user input in real time. This project solves that learning gap by creating a small working application with:

- Offline training scripts.
- Saved models.
- Real-time FastAPI endpoints.
- A browser frontend.
- A local log-file watcher.
- Responsible-use documentation.

## Objectives

The main objectives are:

1. Build a defensive-only phishing and log triage project.
2. Keep training separate from prediction.
3. Load trained models once at API startup.
4. Return immediate JSON results through FastAPI.
5. Provide understandable reasons for each prediction.
6. Demonstrate local real-time monitoring with watchdog.
7. Document limitations, privacy concerns, and responsible use.

## Scope

### Included

- Text/email phishing classification using TF-IDF and Logistic Regression.
- URL phishing classification using explainable URL features and Random Forest.
- Optional external URL checks using API keys from environment variables.
- Rule-based log triage for sanitized Apache/Nginx-style logs.
- Watchdog-based local log monitoring.
- Simple HTML frontend.
- Responsible-use and limitation documentation.

### Not included

- No phishing generation.
- No credential collection.
- No exploitation or scanning.
- No real inbox scraping.
- No production deployment.
- No automatic blocking or enforcement actions.

## System architecture

The project has three major layers.

### 1. Offline training layer

Training scripts are stored in `train/`:

- `train/train_text_model.py`
- `train/train_url_model.py`

These scripts load sanitized datasets from `data/`, train models, evaluate them, and save model files into `models/`.

### 2. Real-time API layer

FastAPI code is stored in `api/`:

- `api/main.py`
- `api/text_analyzer.py`
- `api/url_analyzer.py`
- `api/log_analyzer.py`
- `api/features.py`
- `api/external_checks.py`

The API exposes:

- `GET /health`
- `POST /analyze-text`
- `POST /analyze-url`
- `POST /analyze-log-line`

The text and URL models are loaded once when the API starts. Prediction requests reuse the loaded models and do not retrain.

### 3. User interface and monitoring layer

The UI and monitoring tools are:

- `frontend/index.html`
- `monitor_logs.py`

The frontend calls FastAPI endpoints using `fetch()`. The monitor watches `data/sample_logs.log` and analyzes new lines as they are appended.

## Data used

The project includes small sanitized starter datasets:

- `data/phishing_dataset.csv` with `text,label` columns.
- `data/url_dataset.csv` with `url,label` columns.
- `data/sample_logs.log` with toy Apache/Nginx-style logs.

These datasets are for demonstration only. They are not large enough for production accuracy.

## Text phishing detection method

The text model uses:

- `TfidfVectorizer` to convert text into numeric features.
- `LogisticRegression` to classify text as `legitimate` or `phishing`.

The model is evaluated with:

- Accuracy.
- Precision.
- Recall.
- F1-score.
- Classification report.
- Confusion matrix.

Accuracy alone is not enough because phishing datasets can be imbalanced. Recall is important because missed phishing messages are dangerous, while precision matters because too many false positives can create alert fatigue.

## URL phishing detection method

The URL model uses structural features such as:

- URL length.
- HTTPS usage.
- IP address in hostname.
- Dot count.
- Hyphen count.
- `@` symbol presence.
- Suspicious keyword count.
- Subdomain depth.
- Domain length.
- Special character count.

A `RandomForestClassifier` is trained on these features. The API returns the extracted features so the prediction is easier to explain.

## External checks

Phase 5 adds optional VirusTotal and PhishTank checks. These checks:

- Use environment variables for API keys.
- Are disabled unless `include_external_checks` is set to `true`.
- Return `skipped` when API keys are missing.
- Include privacy warnings.

External checks are supporting evidence only and should not replace human review.

## Log triage method

The log triage module is rule-based. It parses one Apache/Nginx-style log line and checks for:

- Sensitive paths such as `/admin`, `/wp-login`, and `/.env`.
- Repeated `404` responses.
- `401` and `403` statuses.
- Scanning-related file extensions.
- Many different paths requested by the same IP.
- Scanner or bot-like User-Agent text.

The output includes:

- Verdict.
- Risk score.
- Risk level.
- Reasons.
- Parsed log fields.

## Real-time functionality

The project satisfies two real-time requirements:

### Level 1: Real-time API analysis

The user can paste text, URLs, or log lines into the frontend or API. FastAPI returns immediate JSON responses. The trained models are already loaded in memory and are not retrained during prediction.

### Level 2: Real-time monitoring

`monitor_logs.py` uses watchdog to watch a local sample log file. When a new line is appended, the script analyzes it and prints an alert if the risk level is medium or high.

## How to run the project

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Train models

```bash
python -m train.train_text_model
python -m train.train_url_model
```

### 4. Start FastAPI

```bash
uvicorn api.main:app --reload
```

### 5. Open frontend

Open:

```text
frontend/index.html
```

Or serve it locally:

```bash
python -m http.server 8080 --directory frontend
```

Then open:

```text
http://127.0.0.1:8080
```

### 6. Run log monitoring demo

```bash
python monitor_logs.py --file data/sample_logs.log
```

Append a sample line in another terminal:

```bash
printf '%s\n' '203.0.113.50 - - [13/Jun/2026:10:05:00 +0000] "GET /admin HTTP/1.1" 403 300 "-" "Scanner-Test-Agent"' >> data/sample_logs.log
```

## Expected outputs

The system returns JSON results such as:

- `prediction` or `verdict`.
- `confidence`, `score`, or `risk_score`.
- `risk_level`.
- `reasons`.
- `safety_note`.

The frontend displays these results in a readable way.

## Limitations

- Starter datasets are small and not production-grade.
- The text model may overfit obvious keywords.
- URL structural features cannot prove a URL is safe or malicious.
- Rule-based log triage may miss subtle attacks.
- External reputation providers may have incomplete or outdated data.
- The frontend is for local demos only.
- Human review is required.

## Future improvements

Possible extensions include:

- Larger permission-safe datasets.
- Better model evaluation and cross-validation.
- More robust URL feature engineering.
- Optional IsolationForest for log anomaly detection.
- Unit tests and CI.
- Authentication and rate limiting for the API.
- Better frontend design and charts.
- Safe test inbox integration using only a dedicated test account.

## Conclusion

This project demonstrates a complete beginner-friendly defensive workflow: train models offline, load them once in a real-time API, analyze pasted inputs, monitor a local log file, and document responsible use. It is suitable as a college mini-project because it combines Python, machine learning, FastAPI, cybersecurity triage, frontend basics, and ethical limitations in one coherent system.
