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
