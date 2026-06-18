from __future__ import annotations

from api.external_checks import evaluate_sensitive_url, run_external_url_checks


def test_external_checks_disabled_never_submit_to_providers(monkeypatch):
    called = []
    monkeypatch.setattr("api.external_checks.check_virustotal_url", lambda url: called.append(url))
    monkeypatch.setattr("api.external_checks.check_phishtank_url", lambda url: called.append(url))

    result = run_external_url_checks("https://public.example.org/path", enabled=False)

    assert result["enabled"] is False
    assert result["submitted"] is False
    assert result["providers"] == []
    assert called == []


def test_sensitive_query_url_is_blocked_before_provider_calls(monkeypatch):
    called = []
    monkeypatch.setattr("api.external_checks.check_virustotal_url", lambda url: called.append(("vt", url)))
    monkeypatch.setattr("api.external_checks.check_phishtank_url", lambda url: called.append(("pt", url)))

    result = run_external_url_checks("https://public.example.org/reset?session=abc123", enabled=True)

    assert result["enabled"] is True
    assert result["submitted"] is False
    assert result["sensitive_url_filter"]["status"] == "blocked"
    assert "sensitive_query_parameters" in result["sensitive_url_filter"]["categories"]
    assert all(provider["status"] == "skipped" for provider in result["providers"])
    assert called == []


def test_internal_host_is_blocked_before_provider_calls(monkeypatch):
    called = []
    monkeypatch.setattr("api.external_checks.check_virustotal_url", lambda url: called.append(url))
    monkeypatch.setattr("api.external_checks.check_phishtank_url", lambda url: called.append(url))

    result = run_external_url_checks("http://127.0.0.1:8000/status", enabled=True)

    assert result["submitted"] is False
    assert "private_or_internal_host" in result["sensitive_url_filter"]["categories"]
    assert called == []


def test_personal_service_link_is_blocked():
    decision = evaluate_sensitive_url("https://mail.google.com/mail/u/0/#inbox")

    assert decision["safe_to_submit"] is False
    assert "private_service_link" in decision["categories"]


def test_public_url_passes_filter_and_calls_providers(monkeypatch):
    calls = []

    def fake_vt(url):
        calls.append(("virustotal", url))
        return {"provider": "virustotal", "status": "ok"}

    def fake_pt(url):
        calls.append(("phishtank", url))
        return {"provider": "phishtank", "status": "ok"}

    monkeypatch.setattr("api.external_checks.check_virustotal_url", fake_vt)
    monkeypatch.setattr("api.external_checks.check_phishtank_url", fake_pt)

    result = run_external_url_checks("https://public.example.org/news/security-update", enabled=True)

    assert result["submitted"] is True
    assert result["sensitive_url_filter"]["status"] == "safe"
    assert [provider["status"] for provider in result["providers"]] == ["ok", "ok"]
    assert calls == [
        ("virustotal", "https://public.example.org/news/security-update"),
        ("phishtank", "https://public.example.org/news/security-update"),
    ]


def test_token_like_path_value_is_blocked():
    decision = evaluate_sensitive_url("https://public.example.org/a/AbCdEf1234567890AbCdEf1234567890")

    assert decision["safe_to_submit"] is False
    assert "token_like_path_value" in decision["categories"]
