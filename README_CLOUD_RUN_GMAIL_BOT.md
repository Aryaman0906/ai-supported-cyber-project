# Cloud Run Gmail Security Bot Setup

This repository is now cloud-ready, but code alone does **not** deploy Gmail real-time monitoring. You must configure Google Cloud, OAuth consent, Gmail API, Pub/Sub, Cloud Run, Firestore, Secret Manager or environment secrets, Cloud Scheduler, and Drive API.

## Architecture

```text
Gmail inbox change
→ Gmail API users.watch
→ Cloud Pub/Sub topic
→ Pub/Sub push subscription
→ Cloud Run FastAPI /gmail/pubsub/push?token=...
→ decode Pub/Sub message
→ Gmail history.list from stored historyId
→ fetch new INBOX messages
→ analyze subject/snippet/body/URLs
→ apply AI-Cyber labels by risk level
→ store scan metadata
→ daily Markdown/CSV report
→ Google Drive folder "AI Cyber Reports" or local reports/generated/
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

## Required environment variables

- `ENVIRONMENT`
- `GOOGLE_CLOUD_PROJECT`
- `CLOUD_RUN_BASE_URL`
- `GMAIL_OAUTH_REDIRECT_URI`
- `GMAIL_PUBSUB_TOPIC`
- `GOOGLE_OAUTH_CLIENT_SECRET_JSON` or `GOOGLE_OAUTH_CLIENT_SECRET_NAME`
- `TOKEN_ENCRYPTION_KEY`
- `PUBSUB_PUSH_TOKEN`
- `TASK_SHARED_SECRET`
- `STORE_EMAIL_PREVIEWS`
- `STORAGE_BACKEND`
- `LOCAL_STORAGE_PATH`
- `DRIVE_REPORT_FOLDER_NAME`
- `REPORT_OUTPUT_DIR`
- `GMAIL_BOT_USER_EMAIL`

Never commit real credentials, tokens, OAuth client secrets, or personal Gmail data.

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

Open:

```text
http://127.0.0.1:8000/docs
frontend/index.html
```

## Cloud Run deployment

Cloud Run requires the app to listen on `0.0.0.0` and the injected `$PORT`; the Dockerfile uses:

```bash
uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

Deploy from source:

```bash
gcloud run deploy gmail-security-bot \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT,STORAGE_BACKEND=firestore,STORE_EMAIL_PREVIEWS=false
```

For real deployments, prefer Secret Manager instead of large secret values in `--set-env-vars`.

## OAuth consent setup

1. Create an OAuth consent screen in Google Cloud.
2. Add yourself as a test user for personal/testing use.
3. Create a Web application OAuth client.
4. Add redirect URI:
   `https://YOUR_CLOUD_RUN_URL/gmail/auth/callback`.
5. Store the OAuth client JSON in Secret Manager or set `GOOGLE_OAUTH_CLIENT_SECRET_JSON`.
6. Generate a Fernet key for `TOKEN_ENCRYPTION_KEY`:

```bash
python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```

The app uses only these scopes:

- `https://www.googleapis.com/auth/gmail.modify`
- `https://www.googleapis.com/auth/drive.file`

It does **not** use the full `https://mail.google.com/` scope.

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

Create a push subscription to Cloud Run:

```bash
gcloud pubsub subscriptions create gmail-security-bot-push \
  --topic=gmail-security-bot \
  --push-endpoint="https://YOUR_CLOUD_RUN_URL/gmail/pubsub/push?token=YOUR_PUBSUB_PUSH_TOKEN"
```

For production, use authenticated Pub/Sub push with IAM/OIDC rather than only a shared token.

## Gmail watch setup and renewal

1. Complete OAuth: open `/gmail/auth/start`.
2. Start watch: `POST /gmail/watch/start` with your email.
3. Gmail watches expire. Renew daily or at least within 7 days using `/gmail/watch/renew`.
4. Stop watch with `/gmail/watch/stop`.

The watch monitors `INBOX` only and the scanner avoids reprocessing messages already labeled `AI-Cyber/Scanned` unless forced.

## Cloud Scheduler daily maintenance

Create a scheduler job to call `/tasks/daily-maintenance` with header `X-Task-Secret: YOUR_TASK_SHARED_SECRET`.

The endpoint renews the Gmail watch, scans recent inbox messages as fallback, and generates a local daily report. It refuses to run if `TASK_SHARED_SECRET` is not configured.

## Drive reports setup

The OAuth flow includes `drive.file`. `/reports/generate-daily` can upload Markdown and CSV files to a Drive folder named `AI Cyber Reports` when `upload_to_drive=true` and the user has completed OAuth. If Drive upload is not requested, reports are saved locally under `reports/generated/YYYY-MM-DD/`.

## Troubleshooting

- **401 from webhook:** Check `PUBSUB_PUSH_TOKEN` and the push URL query string.
- **403 Gmail API:** Check OAuth consent, test users, scopes, and that Gmail API is enabled.
- **invalid_grant OAuth issue:** Restart OAuth; refresh tokens may have expired or been revoked.
- **watch expired:** Call `/gmail/watch/renew`; schedule daily renewal.
- **Pub/Sub not delivering:** Verify topic, subscription, Cloud Run URL, and Gmail publisher IAM binding.
- **model missing:** Run `python -m train.train_text_model` and `python -m train.train_url_model`; ensure model files are present in the deployed image or generated before deploy.
- **Firestore permission issue:** Grant the Cloud Run service account Firestore permissions.
- **Drive upload permission issue:** Ensure OAuth completed with `drive.file` scope.

## Security notes

- This is a personal/test defensive app unless you complete Google's verification requirements.
- Gmail scopes are sensitive/restricted and must be handled carefully.
- Do not scan private mail without explicit consent.
- Do not store full email bodies by default.
- Do not open links, download attachments, send replies, delete mail, crawl URLs, or detonate files.
- Do not use this as a final security decision system; human review is required.

## Official documentation used

- Gmail push notifications: https://developers.google.com/workspace/gmail/api/guides/push
- Cloud Run container contract: https://docs.cloud.google.com/run/docs/container-contract
- OAuth web server flow: https://developers.google.com/identity/protocols/oauth2/web-server
- Drive uploads/folders: https://developers.google.com/workspace/drive/api/guides/manage-uploads
