# Data folder

This folder contains the small synthetic training datasets used by the defensive phishing detection models.

## Files

| File | Purpose | Columns |
|---|---|---|
| `phishing_dataset.csv` | Text/email phishing classifier training data | `text,label` |
| `url_dataset.csv` | URL phishing classifier training data | `url,label` |

## Dataset policy

- The rows are synthetic or generic examples.
- Do not commit real Gmail message bodies, private inbox data, OAuth tokens, API keys, or personally identifiable information.
- Keep labels limited to `legitimate` and `phishing` unless the training scripts are updated to support more classes.
- Keep the dataset balanced enough that both classes are represented during train/test splitting.

## Cloud recommendation

For this project, the training datasets should stay in GitHub because they are small, synthetic, and useful for reproducibility.

Do not upload real Gmail scan data to a public cloud database. Generated reports may be uploaded to Google Drive for backup/proof, but private email content should remain redacted. A cloud database is only worth adding later if the project becomes multi-user, deployed, or needs a hosted dashboard with persistent shared history.
