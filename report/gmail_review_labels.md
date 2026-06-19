# Gmail Review and Feedback Labels

## Purpose

The Gmail scanner remains non-destructive. It does not delete, archive, spam, forward, or reply to emails. It only applies Gmail labels that help users review risk decisions.

## Automatic labels

The scanner automatically creates and may apply these labels:

- `AI-Cyber/Scanned`
- `AI-Cyber/Low`
- `AI-Cyber/Medium`
- `AI-Cyber/High`
- `AI-Cyber/Needs Review`

High, medium, and low analysis results keep their matching risk labels. Unknown or unrecognized analysis results are labeled `AI-Cyber/Needs Review` so they are separated for manual review instead of being silently mixed into medium-risk mail.

## Manual feedback labels

The scanner creates these feedback labels but does not apply them automatically:

- `AI-Cyber/False Positive`
- `AI-Cyber/Confirmed Phishing`

These labels are for human review after a user checks the message. They help track ML mistakes and confirmed phishing examples without blocking or deleting mail.

## Safety rule

All feedback control stays label-only. The project uses these labels to support review and evaluation; it does not make destructive mailbox changes based on ML output.
