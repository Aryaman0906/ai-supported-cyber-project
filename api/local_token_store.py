"""Local OAuth token storage for the Gmail polling worker.

The default mode prefers OS credential storage through keyring and only falls
back to the legacy plaintext token file when keyring is unavailable.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

SERVICE_NAME = "ai-supported-cyber-project.gmail.local-token"
DEFAULT_ACCOUNT = "default"
VALID_STORAGE_MODES = {"auto", "keyring", "file"}


class LocalTokenStoreError(RuntimeError):
    """Raised when local OAuth token storage cannot be used safely."""


class KeyringBackend(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None: ...
    def set_password(self, service_name: str, username: str, password: str) -> None: ...
    def delete_password(self, service_name: str, username: str) -> None: ...


def _warn(message: str) -> None:
    print(f"WARNING: {message}")


def normalize_storage_mode(mode: str | None = None) -> str:
    selected = (mode or os.getenv("LOCAL_TOKEN_STORAGE") or "auto").strip().lower()
    if selected not in VALID_STORAGE_MODES:
        raise LocalTokenStoreError(
            "LOCAL_TOKEN_STORAGE must be one of: auto, keyring, file. "
            f"Got {selected!r}."
        )
    return selected


def account_key_from_token(token_data: dict[str, Any] | None) -> str:
    """Return a stable keyring account name without exposing token values."""
    if token_data:
        for key in ("account", "email", "emailAddress"):
            value = token_data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
    return DEFAULT_ACCOUNT


def parse_token_json(raw: str, source: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise LocalTokenStoreError(f"Invalid OAuth token JSON in {source}: {error.msg}") from error
    if not isinstance(data, dict):
        raise LocalTokenStoreError(f"Invalid OAuth token JSON in {source}: expected a JSON object.")
    return data


def serialize_token_json(token_data: dict[str, Any]) -> str:
    parse_token_json(json.dumps(token_data), "token data")
    return json.dumps(token_data, sort_keys=True)


def load_keyring_backend() -> KeyringBackend:
    try:
        import keyring  # type: ignore
    except ModuleNotFoundError as error:
        raise LocalTokenStoreError(
            "Python keyring is not installed. Run `pip install -r requirements.txt`, "
            "or explicitly set LOCAL_TOKEN_STORAGE=file for legacy plaintext demo mode."
        ) from error
    return keyring


def assert_keyring_usable(keyring_backend: KeyringBackend) -> None:
    probe_account = f"__probe__{os.getpid()}"
    try:
        keyring_backend.set_password(SERVICE_NAME, probe_account, "probe")
        keyring_backend.get_password(SERVICE_NAME, probe_account)
        try:
            keyring_backend.delete_password(SERVICE_NAME, probe_account)
        except Exception:
            pass
    except Exception as error:
        raise LocalTokenStoreError(
            "OS credential storage through keyring is unavailable or unusable. "
            "Install/configure a keyring backend, or explicitly set LOCAL_TOKEN_STORAGE=file "
            "to use the legacy plaintext token.json fallback for local demos."
        ) from error


def harden_token_file_permissions(token_path: Path) -> None:
    """Best-effort permission hardening for legacy plaintext token files."""
    try:
        if os.name == "nt":
            user = os.getenv("USERNAME") or os.getenv("USER")
            if not user:
                _warn(f"Could not determine current user to harden {token_path} ACLs.")
                return
            commands = [
                ["icacls", str(token_path), "/inheritance:r"],
                ["icacls", str(token_path), "/grant:r", f"{user}:F"],
                ["icacls", str(token_path), "/remove", "Users", "Authenticated Users", "Everyone"],
            ]
            for command in commands:
                subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            token_path.chmod(0o600)
    except Exception as error:
        _warn(f"Could not harden permissions on plaintext OAuth token file {token_path}: {error}")


@dataclass
class LocalOAuthTokenStore:
    token_path: Path
    mode: str | None = None
    keyring_backend: KeyringBackend | None = None
    service_name: str = SERVICE_NAME

    def __post_init__(self) -> None:
        self.token_path = Path(self.token_path)
        self.mode = normalize_storage_mode(self.mode)

    @property
    def backup_dir(self) -> Path:
        return self.token_path.parent / ".local"

    @property
    def backup_path(self) -> Path:
        return self.backup_dir / f"{self.token_path.name}.migrated.bak"

    def load(self) -> dict[str, Any] | None:
        if self.mode == "file":
            return self._load_file()
        backend = self._get_required_keyring() if self.mode == "keyring" else self._get_auto_keyring()
        if backend:
            self._migrate_legacy_file_to_keyring(backend)
            raw = backend.get_password(self.service_name, DEFAULT_ACCOUNT)
            return parse_token_json(raw, "keyring") if raw else None
        _warn("Using legacy plaintext token.json fallback because keyring is unavailable. Set LOCAL_TOKEN_STORAGE=keyring to require OS credential storage.")
        return self._load_file()

    def save(self, token_data: dict[str, Any]) -> None:
        if self.mode == "file":
            self._save_file(token_data)
            return
        backend = self._get_required_keyring() if self.mode == "keyring" else self._get_auto_keyring()
        if backend:
            self._save_keyring(backend, token_data)
            return
        _warn("Saving OAuth token to legacy plaintext token.json because keyring is unavailable.")
        self._save_file(token_data)

    def delete(self) -> None:
        if self.mode != "file":
            backend = self._get_auto_keyring() if self.mode == "auto" else self._get_required_keyring()
            if backend:
                try:
                    backend.delete_password(self.service_name, DEFAULT_ACCOUNT)
                except Exception:
                    pass
        try:
            self.token_path.unlink()
        except FileNotFoundError:
            pass

    def _load_file(self) -> dict[str, Any] | None:
        if not self.token_path.exists():
            return None
        _warn(f"Using plaintext OAuth token file {self.token_path}. This fallback is for local demos only.")
        return parse_token_json(self.token_path.read_text(encoding="utf-8"), str(self.token_path))

    def _save_file(self, token_data: dict[str, Any]) -> None:
        _warn(f"Writing plaintext OAuth token file {self.token_path}. This fallback is for local demos only.")
        self.token_path.write_text(serialize_token_json(token_data), encoding="utf-8")
        harden_token_file_permissions(self.token_path)

    def _get_auto_keyring(self) -> KeyringBackend | None:
        try:
            backend = self.keyring_backend or load_keyring_backend()
            assert_keyring_usable(backend)
            return backend
        except LocalTokenStoreError:
            return None

    def _get_required_keyring(self) -> KeyringBackend:
        backend = self.keyring_backend or load_keyring_backend()
        assert_keyring_usable(backend)
        return backend

    def _save_keyring(self, backend: KeyringBackend, token_data: dict[str, Any]) -> None:
        serialized = serialize_token_json(token_data)
        backend.set_password(self.service_name, DEFAULT_ACCOUNT, serialized)
        account = account_key_from_token(token_data)
        if account != DEFAULT_ACCOUNT:
            backend.set_password(self.service_name, account, serialized)

    def _migrate_legacy_file_to_keyring(self, backend: KeyringBackend) -> None:
        if not self.token_path.exists():
            return
        token_data = parse_token_json(self.token_path.read_text(encoding="utf-8"), str(self.token_path))
        self._save_keyring(backend, token_data)
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            if self.backup_path.exists():
                self.backup_path.unlink()
            shutil.move(str(self.token_path), str(self.backup_path))
            harden_token_file_permissions(self.backup_path)
            _warn(f"Migrated legacy plaintext {self.token_path.name} into OS credential storage and moved the old file to {self.backup_path}.")
        except Exception as error:
            _warn(
                f"Migrated legacy plaintext {self.token_path.name} into OS credential storage, "
                f"but could not move the old file aside ({error}). Delete it after confirming Gmail auth still works."
            )
