# Cloud Run Gmail Security Bot Setup

This file is **future optional deployment guidance**. It is not the current submitted architecture.

The current working project architecture is local scheduled automation:

```text
Windows Task Scheduler
→ local Gmail polling script
→ Gmail API scan
→ AI-Cyber labels
→ local Markdown/CSV/XLSX reports
→ optional Google Drive report upload
```

Use the Cloud Run/Pub/Sub design only after authentication, IAM, OAuth consent, protected runtime configuration, and report privacy are hardened.

## Cloud deployment safety rule

Do **not** expose Gmail, OAuth, Pub/Sub, report, scan, log, or maintenance endpoints as public anonymous endpoints.

For any real cloud deployment:

- require Cloud Run IAM authentication, IAP, API Gateway, or another access-control layer;
- grant invoker access only to approved users or service accounts;
- use authenticated Pub/Sub push with OIDC/IAM;
- store protected application configuration in Secret Manager;
- keep email preview storage disabled unless there is explicit consent and a privacy reason;
- use a dedicated Cloud Run service account with minimum required permissions.

## Optional cloud architecture

```text
Gmail inbox change
→ Gmail API users.watch
→ Cloud Pub/Sub topic
→ authenticated Pub/Sub push subscription
→ Cloud Run FastAPI webhook
→ Gmail history.list from stored historyId
→ fetch new INBOX messages
→ analyze subject/snippet/body/URLs
→ apply AI-Cyber labels by risk level
→ store scan metadata
→ daily Markdown/CSV report
→ Google Drive folder or local reports/generated/
```

## Required Google Cloud APIs

Enable these APIs in the project:

- Gmail API
- Pub/Sub API
- Cloud Run API
- Firestore API
- Secret Manager API
- Drive API
- Cloud Scheduler API

Never commit real credentials, runtime config, Drive links, generated reports, logs, or personal Gmail data.

## Local development commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m train.train_text_model
python -m train.train_url_model
uvicorn api.main:app --reload
python tests/phase_completion_check.py
python tests/cloud_gmail_bot_check.py
pytest
```

Open locally only:

```text
http://127.0.0.1:8000/docs
frontend/index.html
```

## Cloud Run deployment: authenticated only

Cloud Run requires the app to listen on `0.0.0.0` and the injected `$PORT`; the Dockerfile uses:

```bash
uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

Deploy from source without granting anonymous/public invoker access:

```bash
gcloud run deploy gmail-security-bot \
  --source . \
  --region us-central1 \
  --set-env-vars ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT,STORAGE_BACKEND=firestore,STORE_EMAIL_PREVIEWS=false
```

Then grant invoker access only to a specific approved principal:

```bash
gcloud run services add-iam-policy-binding gmail-security-bot \
  --region us-central1 \
  --member="user:YOUR_EMAIL@example.com" \
  --role="roles/run.invoker"
```

For real deployments, prefer Secret Manager instead of large values in environment variables.

## OAuth consent setup

1. Create an OAuth consent screen in Google Cloud.
2. Add yourself as a test user for personal/testing use.
3. Create a Web application OAuth client.
4. Add redirect URI: `https://YOUR_CLOUD_RUN_URL/gmail/auth/callback`.
5. Store OAuth client configuration in Secret Manager or another protected runtime configuration system.

## Pub/Sub setup

Create the topic:

```bash
gcloud pubsub topics create gmail-security-bot
```

Grant Gmail's publisher service account permission to publish:

```bash
gcloud pubsub topics add-iam-policy-binding gmail-security-bot \
  --member=serviceAccount:gmail-api-push@system.gserviceaccount.com \
  --role=roles/pubsub.publisher
```

Create a push subscription only after Cloud Run invoker access and Pub/Sub OIDC authentication are configured:

```bash
gcloud pubsub subscriptions create gmail-security-bot-push \
  --topic=gmail-security-bot \
  --push-endpoint="https://YOUR_CLOUD_RUN_URL/gmail/pubsub/push" \
  --push-auth-service-account=YOUR_PUBSUB_PUSH_SERVICE_ACCOUNT@YOUR_PROJECT.iam.gserviceaccount.com
```

Do not rely on a query-string value as the only protection for a deployed webhook.

## Gmail watch setup and renewal

1. Complete OAuth: open `/gmail/auth/start`.
2. Start watch: `POST /gmail/watch/start` with your email.
3. Gmail watches expire. Renew daily or at least within 7 days using `/gmail/watch/renew`.
4. Stop watch with `/gmail/watch/stop`.

The watch monitors `INBOX` only and the scanner avoids reprocessing messages already labeled `AI-Cyber/Scanned` unless forced.

## Cloud Scheduler daily maintenance

Create a scheduler job to call `/tasks/daily-maintenance` with an internal authentication mechanism.

The endpoint renews the Gmail watch, scans recent inbox messages as fallback, and generates a local daily report. In production, protect scheduler calls with IAM/OIDC and an application-level guard.

## Drive reports setup

`/reports/generate-daily` can upload Markdown and CSV files to a Drive folder named `AI Cyber Reports` when Drive upload is requested and the user has completed OAuth. If Drive upload is not requested, reports are saved locally under `reports/generated/YYYY-MM-DD/`.

For real deployments, verify Drive folder permissions before enabling upload. Do not upload reports containing private subjects, snippets, full message IDs, personal addresses, or sensitive URLs unless you have consent and a retention policy.

## Troubleshooting

- **401 from webhook:** Check Cloud Run IAM and Pub/Sub OIDC service account permissions.
- **403 Gmail API:** Check OAuth consent, test users, scopes, and that Gmail API is enabled.
- **403 Cloud Run invocation:** Check that the caller has `roles/run.invoker` on the service.
- **watch expired:** Call `/gmail/watch/renew`; schedule daily renewal.
- **Pub/Sub not delivering:** Verify topic, subscription, push service account, Cloud Run URL, and Gmail publisher IAM binding.
- **model missing:** Run `python -m train.train_text_model` and `python -m train.train_url_model`; ensure model files are present in the deployed image or generated before deploy.
- **Firestore permission issue:** Grant the Cloud Run service account Firestore permissions.
- **Drive upload permission issue:** Ensure Drive folder access is correct.

## Security notes

- This is a personal/test defensive app unless you complete Google's verification requirements.
- Gmail scopes are sensitive/restricted and must be handled carefully.
- Do not scan private mail without explicit consent.
- Do not store full email bodies by default.
- Do not open links, download attachments, send replies, delete mail, crawl URLs, or detonate files.
- Do not use this as a final security decision system; human review is required.
- Do not publish scan, report, log, OAuth, Gmail watch, or maintenance endpoints without authentication.
- Treat Cloud Run/Pub/Sub as future optional scope for the current project unless you can prove a secure authenticated deployment.

## Official documentation used

- Gmail push notifications: https://developers.google.com/workspace/gmail/api/guides/push
- Cloud Run container contract: https://docs.cloud.google.com/run/docs/container-contract
- OAuth web server flow: https://developers.google.com/identity/protocols/oauth2/web-server
- Drive uploads/folders: https://developers.google.com/workspace/drive/api/guides/manage-uploads
