"""Gmail OAuth helpers for the Cloud Run Gmail Security Bot."""
from __future__ import annotations

import json, os, secrets
from typing import Any

from api.storage import BotStorage

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive.file",
]

class OAuthConfigurationError(RuntimeError):
    pass


def gmail_oauth_config_status() -> dict[str, Any]:
    return {
        "oauth_client_configured": bool(os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_JSON") or os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_NAME")),
        "token_encryption_key_configured": bool(os.getenv("TOKEN_ENCRYPTION_KEY")),
        "redirect_uri_configured": bool(os.getenv("GMAIL_OAUTH_REDIRECT_URI") or os.getenv("CLOUD_RUN_BASE_URL")),
        "scopes": GMAIL_SCOPES,
    }


def get_redirect_uri() -> str:
    redirect = os.getenv("GMAIL_OAUTH_REDIRECT_URI")
    if redirect:
        return redirect
    base = os.getenv("CLOUD_RUN_BASE_URL")
    if base:
        return base.rstrip("/") + "/gmail/auth/callback"
    raise OAuthConfigurationError("GMAIL_OAUTH_REDIRECT_URI or CLOUD_RUN_BASE_URL is required for OAuth")


def load_oauth_client_config() -> dict[str, Any]:
    raw = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_JSON")
    if raw:
        return json.loads(raw)
    secret_name = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_NAME")
    if secret_name:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": secret_name})
        return json.loads(response.payload.data.decode("utf-8"))
    raise OAuthConfigurationError("OAuth client is not configured. Set GOOGLE_OAUTH_CLIENT_SECRET_JSON or GOOGLE_OAUTH_CLIENT_SECRET_NAME.")


def _fernet():
    key = os.getenv("TOKEN_ENCRYPTION_KEY")
    if not key:
        raise OAuthConfigurationError("TOKEN_ENCRYPTION_KEY is required to encrypt OAuth tokens")
    from cryptography.fernet import Fernet
    return Fernet(key.encode("utf-8") if isinstance(key, str) else key)


def encrypt_token_data(token_data: dict[str, Any]) -> str:
    return _fernet().encrypt(json.dumps(token_data).encode("utf-8")).decode("utf-8")


def decrypt_token_data(encrypted_token: str) -> dict[str, Any]:
    return json.loads(_fernet().decrypt(encrypted_token.encode("utf-8")).decode("utf-8"))


def build_flow(state: str | None = None):
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(load_oauth_client_config(), scopes=GMAIL_SCOPES, state=state)
    flow.redirect_uri = get_redirect_uri()
    return flow


def create_authorization_url(storage: BotStorage) -> dict[str, str]:
    state = secrets.token_urlsafe(24)
    storage.save_account("__oauth_state__", {"state": state})
    flow = build_flow(state=state)
    url, returned_state = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
    return {"authorization_url": url, "state": returned_state, "scopes": " ".join(GMAIL_SCOPES)}


def exchange_callback_for_token(storage: BotStorage, request_url: str, state: str | None) -> dict[str, Any]:
    expected = (storage.get_account("__oauth_state__") or {}).get("state")
    if expected and state != expected:
        raise OAuthConfigurationError("OAuth state mismatch; restart authorization")
    flow = build_flow(state=state)
    flow.fetch_token(authorization_response=request_url)
    credentials = flow.credentials
    from googleapiclient.discovery import build
    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
    profile = service.users().getProfile(userId="me").execute()
    email = profile["emailAddress"]
    token_data = json.loads(credentials.to_json())
    storage.save_encrypted_token(email, encrypt_token_data(token_data))
    storage.save_account(email, {"email": email, "oauth_configured": True})
    return {"email": email, "status": "authorized", "scopes": GMAIL_SCOPES}


def credentials_for_email(storage: BotStorage, email: str):
    encrypted = storage.get_encrypted_token(email)
    if not encrypted:
        raise OAuthConfigurationError(f"No stored OAuth token for {email}; start /gmail/auth/start first")
    from google.oauth2.credentials import Credentials
    return Credentials.from_authorized_user_info(decrypt_token_data(encrypted), scopes=GMAIL_SCOPES)
