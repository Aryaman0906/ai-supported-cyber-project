# Security Architecture

## Security architecture summary

This project is a defensive-only cybersecurity student/demo system. It helps identify potentially risky Gmail messages, URLs, and log events, but it does not perform offensive testing, credential collection, exploitation, or destructive email actions.

The submitted Gmail automation architecture uses near-real-time scheduled polling from a local Windows environment. It is not full real-time Gmail Pub/Sub push monitoring and it is not a full cloud-native Cloud Run deployment. Gmail access occurs only after a user explicitly authorizes the application through OAuth.

## Actual working architecture

```text
User-authorized Gmail account
        ↓
Gmail API OAuth
        ↓
Windows Task Scheduler
        ↓
Local Gmail polling worker
        ↓
Email parsing and feature extraction
        ↓
Text model + URL model + rules
        ↓
Risk scoring
        ↓
Gmail labels
        ↓
Local reports
        ↓
Optional Google Drive upload
```

The local scheduler periodically starts the Gmail polling worker. The worker scans recent inbox messages through the Gmail API, skips messages already marked as scanned, parses message content safely, analyzes text and URL indicators, applies Gmail labels, generates local Markdown/CSV/XLSX reports, and can optionally upload those reports to Google Drive.

| Security decision | Reason |
|---|---|
| Scheduled polling instead of Pub/Sub | Avoids paid cloud dependencies |
| Gmail labels instead of deletion | Prevents destructive false positives |
| Local OAuth token storage prefers OS credential storage | Reduces plaintext token exposure |
| Reports generated with metadata only | Reduces privacy exposure |
| Drive upload optional | Keeps cloud dependency limited |

## Assets protected

The project is designed to protect or reduce exposure of:

- The user's Gmail account and OAuth tokens.
- Email metadata, message snippets, sender details, subjects, URL indicators, and risk reasons.
- Local generated reports in Markdown, CSV, and XLSX formats.
- Local runtime state used to skip already scanned messages.
- API keys for optional third-party URL reputation checks.
- Local model artifacts and datasets used by the demo system.

## Trust boundaries

The main trust boundaries are:

- The user-authorized Gmail account and Google's Gmail API.
- The local Windows scheduler and local project directory.
- The local Gmail polling worker and local storage/report files.
- Optional Google Drive upload through the Drive API.
- Optional external URL reputation providers when explicitly enabled.

Cloud Run, Pub/Sub, and a cloud SOC backend are future optional scope only. They are not the current submitted Gmail automation architecture.

## Identity and access control

Gmail access happens only after explicit user OAuth authorization. The application does not bypass login, scrape an inbox without permission, or access arbitrary Gmail accounts. OAuth tokens represent the authorizing user and should be treated as sensitive local secrets.

Access should follow least privilege as much as the configured Gmail and Drive scopes allow. If a user revokes OAuth consent, the local worker can no longer access that account through the API.

## Gmail and Drive API permission model

The Gmail API is used for authorized inbox polling, reading message metadata/content needed for analysis, and applying Gmail labels. The system uses Gmail labels as a non-destructive response mechanism instead of deleting, forwarding, replying to, or blocking emails.

The Drive API is optional and is used only for report backup/storage. Google Drive is not used as a full cloud security backend, alerting platform, or SOC system in the submitted architecture.

## Local execution security

The working automation runs locally through this chain:

```text
Windows Task Scheduler
→ run_gmail_poll_hidden.vbs
→ run_gmail_poll_once.bat
→ api.gmail_poll_worker
```

The scheduled task should run under the intended local user account. Project files, OAuth tokens, logs, and reports should be stored in a local directory with appropriate filesystem permissions.

## Email parsing and content safety

HTML and plain-text emails are parsed for defensive analysis. HTML content must be treated as untrusted input. Scripts, styles, and active content must not be executed. HTML should be converted to text and links should be extracted as indicators.

Suspicious links are analyzed as indicators. The tool must not open links in a browser, visit login pages, submit forms, or interact with suspicious sites.

## Detection and risk scoring security

The project combines machine-learning predictions, URL feature analysis, and rules to produce risk scores and labels. These results are assistive signals only. Human review is required before taking action because false positives and false negatives are expected in a student/demo system.

Optional external threat-intelligence checks may disclose submitted URLs to third-party services. For privacy and data-minimization reasons, those checks must remain optional and should be enabled only when the user understands that disclosure.

## Gmail response model

The response model is intentionally non-destructive. The system applies Gmail labels such as low, medium, high, and scanned indicators. It does not automatically delete emails, forward emails, reply to senders, block senders, or quarantine messages outside Gmail's normal label model.

This design reduces harm from false positives and keeps the user in control of final decisions.

## Reporting and Google Drive security

The system generates local reports in Markdown, CSV, and XLSX formats. Reports summarize scan metadata, risk levels, scores, labels, and reasons. Reports should avoid unnecessary full-message content to reduce privacy exposure.

Reports can optionally be uploaded to Google Drive using the Drive API. This is for backup/storage convenience only. Google Drive is not the current security backend and should not be treated as a cloud SOC replacement.

## Data privacy controls

Privacy controls include:

- Authorized Gmail access only after explicit OAuth consent.
- Local scheduled polling instead of always-on cloud processing.
- Metadata-focused reports rather than unnecessary full email dumps.
- Optional Google Drive upload instead of mandatory cloud storage.
- Optional external URL reputation checks because they may disclose URLs.
- Human review before acting on risk results.

## Secret and token handling

Local OAuth token storage now prefers OS credential storage through `keyring`. Plaintext `token.json` remains only as an explicit legacy fallback or as a migration source for older local setups. Environment files and local runtime files should also stay out of version control.

Generated reports, logs, runtime files, local storage, model artifacts, credentials, tokens, and API keys must not be committed. This includes `.env`, `.local`, `reports/generated`, runtime directories, token files, and local model files.

## Threat model

Important threats include:

- OAuth token leakage through accidental commits or insecure local storage.
- Exposure of private email metadata through reports or Drive uploads.
- Incorrect classification that labels legitimate email as risky or misses phishing.
- Unsafe handling of HTML email content.
- Privacy leakage when optional third-party URL checks are enabled.
- Over-trusting demo model output without human review.

The project mitigates these risks with OS credential storage for local OAuth tokens where available, Git ignore rules, non-destructive Gmail labels, safe parsing expectations, optional external checks, and explicit human review requirements. Plaintext token files are limited to explicit fallback/demo mode or one-time migration sources.

## Security limitations

This is a student/demo system, not a production email security gateway. Limitations include:

- Near-real-time scheduled Gmail polling, not full real-time Gmail Pub/Sub push monitoring.
- No full cloud-native SOC deployment in the submitted version.
- Expected false positives and false negatives.
- Limited demo datasets and model coverage.
- No guaranteed protection against novel phishing campaigns.
- No automatic deletion, forwarding, replying, blocking, or enterprise quarantine.
- Local machine security directly affects token and report security.
- For real deployments, use managed secrets or encrypted token storage rather than local plaintext token files.

## Future security improvements

Future optional work could include:

- A carefully scoped Cloud Run/Pub/Sub architecture for users who want cloud-hosted push processing.
- More granular Gmail and Drive scopes where possible.
- Report encryption or password-protected archives.
- Better model evaluation with larger sanitized datasets.
- Safer URL detonation through isolated sandbox services.
- Admin dashboards, audit trails, and alert review workflows.
