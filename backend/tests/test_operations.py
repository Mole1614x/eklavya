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
        database_url="postgresql+psycopg://app:secret@db:5432/eklavya",
        redis_url="redis://:cache-secret@redis:6379/0", public_url="https://learn.example.com",
        rate_limit_enabled=True, readiness_check_redis=True,
        _env_file=None,
    )
    assert configured.origin_list == ["https://learn.example.com"]
    assert configured.host_list == ["learn.example.com", "backend"]


@pytest.mark.parametrize("field,value", [
    ("database_url", "sqlite:///production.db"),
    ("redis_url", "http://redis:6379"),
    ("public_url", "http://learn.example.com"),
    ("allowed_origins", "http://learn.example.com"),
])
def test_production_settings_reject_insecure_dependencies(field, value):
    values = {
        "environment": "production",
        "secret_key": "a-unique-production-secret-that-is-long-enough",
        "allowed_origins": "https://learn.example.com",
        "allowed_hosts": "learn.example.com,backend",
        "database_url": "postgresql+psycopg://app:secret@db:5432/eklavya",
        "redis_url": "redis://:cache-secret@redis:6379/0",
        "public_url": "https://learn.example.com",
        "rate_limit_enabled": True,
        "readiness_check_redis": True,
        "_env_file": None,
    }
    values[field] = value
    with pytest.raises(ValidationError):
        Settings(**values)


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
        assert "eklavya_judge_oldest_queued_seconds" in metrics.text
        assert "eklavya_database_up" in metrics.text


def test_untrusted_hosts_are_rejected():
    response = TestClient(app).get("/api/v1/health", headers={"host": "attacker.example"})
    assert response.status_code == 400


def test_cors_returns_credentials_only_to_allowlisted_origins():
    with TestClient(app) as client:
        allowed = client.options("/api/v1/auth/login", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        })
        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
        denied = client.options("/api/v1/auth/login", headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "POST",
        })
        assert "access-control-allow-origin" not in denied.headers
