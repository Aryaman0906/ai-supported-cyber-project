from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None and importlib.util.find_spec("httpx") is not None

if HAS_FASTAPI:
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
else:
    client = None


@pytest.mark.skipif(HAS_FASTAPI, reason="source fallback only needed when FastAPI is unavailable")
def test_polling_admin_auth_source_is_configured_without_fastapi_dependency():
    source = Path("api/main.py").read_text(encoding="utf-8")

    assert "def require_local_admin" in source
    assert "LOCAL_ADMIN_TOKEN" in source
    assert "X-Local-Admin-Token" in source
    for route in (
        '@app.get("/polling/status", dependencies=[Depends(require_local_admin)])',
        '@app.post("/polling/scan-now", dependencies=[Depends(require_local_admin)])',
        '@app.post("/polling/report-today", dependencies=[Depends(require_local_admin)])',
        '@app.get("/polling/latest-log", dependencies=[Depends(require_local_admin)])',
        '@app.get("/polling/reports", dependencies=[Depends(require_local_admin)])',
    ):
        assert route in source


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI test client dependencies are unavailable")
def test_polling_endpoint_requires_configured_admin_token(monkeypatch):
    monkeypatch.delenv("LOCAL_ADMIN_TOKEN", raising=False)

    response = client.get("/polling/reports")

    assert response.status_code == 503
    assert response.json()["detail"] == "LOCAL_ADMIN_TOKEN is not configured"


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI test client dependencies are unavailable")
def test_polling_endpoint_rejects_missing_admin_header(monkeypatch):
    monkeypatch.setenv("LOCAL_ADMIN_TOKEN", "test-token")

    response = client.get("/polling/reports")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid local admin token"


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI test client dependencies are unavailable")
def test_polling_endpoint_rejects_wrong_admin_header(monkeypatch):
    monkeypatch.setenv("LOCAL_ADMIN_TOKEN", "test-token")

    response = client.get(
        "/polling/reports",
        headers={"X-Local-Admin-Token": "wrong-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid local admin token"


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI test client dependencies are unavailable")
def test_polling_read_only_endpoints_accept_correct_admin_header(monkeypatch):
    monkeypatch.setenv("LOCAL_ADMIN_TOKEN", "test-token")
    headers = {"X-Local-Admin-Token": "test-token"}

    for path in ("/polling/status", "/polling/latest-log", "/polling/reports"):
        response = client.get(path, headers=headers)
        assert response.status_code == 200
