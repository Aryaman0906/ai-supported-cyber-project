from __future__ import annotations

import json

import pytest

from api.local_token_store import LocalOAuthTokenStore, LocalTokenStoreError, harden_token_file_permissions

DUMMY_TOKEN = {
    "token": "at-dummy",
    "refresh_token": "rt-dummy",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": "cid-dummy",
    "client_secret": "cs-dummy",
    "scopes": ["https://www.googleapis.com/auth/gmail.modify"],
}


class FakeKeyring:
    def __init__(self, fail=False):
        self.values = {}
        self.fail = fail

    def get_password(self, service_name, username):
        if self.fail:
            raise RuntimeError("keyring unavailable")
        return self.values.get((service_name, username))

    def set_password(self, service_name, username, password):
        if self.fail:
            raise RuntimeError("keyring unavailable")
        self.values[(service_name, username)] = password

    def delete_password(self, service_name, username):
        if self.fail:
            raise RuntimeError("keyring unavailable")
        self.values.pop((service_name, username), None)


def test_fake_keyring_backend_can_save_load_and_delete_token_json(tmp_path):
    keyring = FakeKeyring()
    token_path = tmp_path / "token.json"
    store = LocalOAuthTokenStore(token_path, mode="keyring", keyring_backend=keyring)

    store.save(DUMMY_TOKEN)

    assert store.load() == DUMMY_TOKEN
    store.delete()
    assert store.load() is None


def test_keyring_mode_does_not_write_plaintext_token_json(tmp_path):
    keyring = FakeKeyring()
    token_path = tmp_path / "token.json"
    store = LocalOAuthTokenStore(token_path, mode="keyring", keyring_backend=keyring)

    store.save(DUMMY_TOKEN)

    assert not token_path.exists()
    assert store.load()["refresh_token"] == "rt-dummy"


def test_migration_reads_legacy_token_file_and_moves_backup(tmp_path):
    keyring = FakeKeyring()
    token_path = tmp_path / "token.json"
    token_path.write_text(json.dumps(DUMMY_TOKEN), encoding="utf-8")
    store = LocalOAuthTokenStore(token_path, mode="keyring", keyring_backend=keyring)

    assert store.load() == DUMMY_TOKEN

    assert not token_path.exists()
    backup_path = tmp_path / ".local" / "token.json.migrated.bak"
    assert backup_path.exists()
    assert json.loads(backup_path.read_text(encoding="utf-8"))["token"] == "at-dummy"
    assert store.load() == DUMMY_TOKEN


def test_file_mode_writes_token_file_and_hardens_permissions(tmp_path, monkeypatch):
    calls = []

    def fake_harden(path):
        calls.append(path)

    monkeypatch.setattr("api.local_token_store.harden_token_file_permissions", fake_harden)
    token_path = tmp_path / "token.json"
    store = LocalOAuthTokenStore(token_path, mode="file", keyring_backend=FakeKeyring(fail=True))

    store.save(DUMMY_TOKEN)

    assert json.loads(token_path.read_text(encoding="utf-8"))["client_id"] == "cid-dummy"
    assert calls == [token_path]


def test_invalid_corrupt_token_json_gives_clear_error(tmp_path):
    token_path = tmp_path / "token.json"
    token_path.write_text("{not-json", encoding="utf-8")
    store = LocalOAuthTokenStore(token_path, mode="file")

    with pytest.raises(LocalTokenStoreError, match="Invalid OAuth token JSON"):
        store.load()


def test_posix_permission_hardening_uses_chmod(tmp_path, monkeypatch):
    token_path = tmp_path / "token.json"
    token_path.write_text("{}", encoding="utf-8")
    chmod_calls = []
    monkeypatch.setattr("api.local_token_store.os.name", "posix")
    monkeypatch.setattr("api.local_token_store.Path.chmod", lambda self, mode: chmod_calls.append((self, mode)))

    harden_token_file_permissions(token_path)

    assert chmod_calls == [(token_path, 0o600)]
