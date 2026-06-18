from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None

if HAS_FASTAPI:
    from fastapi import HTTPException, status

    from api.main import (
        app,
        local_polling_latest_log,
        local_polling_reports,
        local_polling_status,
        require_local_admin,
    )


PROTECTED_ROUTES = {
    "/polling/status",
    "/polling/scan-now",
    "/polling/report-today",
    "/polling/latest-log",
    "/polling/reports",
    "/reports/generate-daily",
    "/reports/today",
    "/reports/{report_date}",
}


@pytest.mark.skipif(HAS_FASTAPI, reason="source fallback only needed when FastAPI is unavailable")
def test_polling_admin_auth_source_is_configured_without_fastapi_dependency():
    source = Path("api/main.py").read_text(encoding="utf-8")

    assert "def require_local_admin" in source
    assert "LOCAL_ADMIN_TOKEN" in source
    assert "X-Local-Admin-Token" in source
    for route in PROTECTED_ROUTES:
        assert f'"{route}"' in source
        assert "dependencies=[Depends(require_local_admin)]" in source


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI dependency is unavailable")
def test_polling_endpoint_requires_configured_admin_token(monkeypatch):
    monkeypatch.delenv("LOCAL_ADMIN_TOKEN", raising=False)

    with pytest.raises(HTTPException) as error:
        require_local_admin("test-token")

    assert error.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert error.value.detail == "LOCAL_ADMIN_TOKEN is not configured"


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI dependency is unavailable")
def test_polling_endpoint_rejects_missing_admin_header(monkeypatch):
    monkeypatch.setenv("LOCAL_ADMIN_TOKEN", "test-token")

    with pytest.raises(HTTPException) as error:
        require_local_admin(None)

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert error.value.detail == "Invalid local admin token"


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI dependency is unavailable")
def test_polling_endpoint_rejects_wrong_admin_header(monkeypatch):
    monkeypatch.setenv("LOCAL_ADMIN_TOKEN", "test-token")

    with pytest.raises(HTTPException) as error:
        require_local_admin("wrong-token")

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert error.value.detail == "Invalid local admin token"


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI dependency is unavailable")
def test_polling_read_only_endpoints_accept_correct_admin_header(monkeypatch):
    monkeypatch.setenv("LOCAL_ADMIN_TOKEN", "test-token")

    assert require_local_admin("test-token") is None
    assert isinstance(local_polling_status(), dict)
    assert isinstance(local_polling_latest_log(), dict)
    assert isinstance(local_polling_reports(), dict)


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI dependency is unavailable")
def test_protected_routes_use_local_admin_dependency():
    protected_routes = {
        route.path: route
        for route in app.routes
        if getattr(route, "path", None) in PROTECTED_ROUTES
    }

    assert set(protected_routes) == PROTECTED_ROUTES
    for route in protected_routes.values():
        dependency_calls = [dependency.dependency for dependency in route.dependencies]
        assert require_local_admin in dependency_calls
