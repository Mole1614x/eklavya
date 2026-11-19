import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import app
from app.operations import MemoryLimiter


def test_production_settings_require_real_secrets_and_explicit_origins():
    with pytest.raises(ValidationError):
        Settings(environment="production", _env_file=None)
    configured = Settings(
        environment="production", secret_key="a-unique-production-secret-that-is-long-enough",
        allowed_origins="https://learn.example.com", allowed_hosts="learn.example.com,backend",
        _env_file=None,
    )
    assert configured.origin_list == ["https://learn.example.com"]
    assert configured.host_list == ["learn.example.com", "backend"]


def test_memory_rate_limiter_uses_fixed_windows():
    limiter = MemoryLimiter()
    assert limiter.hit("login:client", 2, 60, now=100)[0] is True
    assert limiter.hit("login:client", 2, 60, now=101)[0] is True
    allowed, retry_after = limiter.hit("login:client", 2, 60, now=102)
    assert allowed is False
    assert retry_after == 58
    assert limiter.hit("login:client", 2, 60, now=161)[0] is True


def test_request_ids_security_headers_and_metrics():
    with TestClient(app) as client:
        response = client.get("/api/v1/health/live", headers={"X-Request-ID": "test-request-123"})
        assert response.status_code == 200
        assert response.headers["x-request-id"] == "test-request-123"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        metrics = client.get("/api/v1/metrics")
        assert "eklavya_http_requests_total" in metrics.text


def test_untrusted_hosts_are_rejected():
    response = TestClient(app).get("/api/v1/health", headers={"host": "attacker.example"})
    assert response.status_code == 400
