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
python train/train_text_model.py
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
python train/train_text_model.py
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
python train/train_text_model.py
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
  "detail": "Text model not found ... Run: python train/train_text_model.py"
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
python train/train_text_model.py
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
python train/train_text_model.py
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
python train/train_url_model.py
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
python train/train_url_model.py
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
python train/train_url_model.py
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
