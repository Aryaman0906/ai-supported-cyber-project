# Data folder

This project uses safe starter datasets for defensive learning. This PR does **not** add huge real phishing datasets because public data requires licensing, privacy, source-quality, and safety review first.

## Folder structure

```text
data/
├── raw/                  # safe synthetic source examples
├── processed/            # metadata-rich master datasets
├── phishing_dataset.csv  # final training text CSV used by train/train_text_model.py
└── url_dataset.csv       # final training URL CSV used by train/train_url_model.py
```

## Schemas

### raw/synthetic_text_examples.csv and processed/phishing_dataset_master.csv

```csv
text,label,source,category,notes
```

### raw/synthetic_url_examples.csv and processed/url_dataset_master.csv

```csv
url,label,source,category,date_added
```

### Final training files

`data/phishing_dataset.csv` keeps exactly:

```csv
text,label
```

`data/url_dataset.csv` keeps exactly:

```csv
url,label
```

Existing training scripts depend on these final two-column files and do not need path changes.

## Privacy and safety rules

Do not commit:

- Real Gmail bodies or inbox exports.
- OAuth tokens, credentials, API keys, or `.env` files.
- Generated reports or private logs.
- Personally identifiable information.
- Live malicious URLs or real phishing infrastructure.

Use synthetic/generic examples, reserved domains, `.test`, `.invalid`, and RFC example IP ranges only for starter data.

## Rebuild datasets

```bash
python tools/build_datasets.py
```

The builder cleans labels, normalizes whitespace, removes empty rows, deduplicates, balances classes by downsampling to the smaller class, writes metadata-rich master datasets, and exports training-compatible final CSVs.

## Retrain models

```bash
python -m train.train_text_model
python -m train.train_url_model
```
