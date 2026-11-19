import hashlib
import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .config import Settings

logger = logging.getLogger("eklavya.requests")
REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("request_id", "method", "path", "status", "duration_ms"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.requests = 0
        self.errors = 0
        self.duration_seconds = 0.0

    def observe(self, status_code: int, duration_seconds: float) -> None:
        with self._lock:
            self.requests += 1
            self.errors += int(status_code >= 500)
            self.duration_seconds += duration_seconds

    def render(self) -> str:
        with self._lock:
            return (
                "# HELP eklavya_http_requests_total Total HTTP requests.\n"
                "# TYPE eklavya_http_requests_total counter\n"
                f"eklavya_http_requests_total {self.requests}\n"
                "# HELP eklavya_http_errors_total Total 5xx responses.\n"
                "# TYPE eklavya_http_errors_total counter\n"
                f"eklavya_http_errors_total {self.errors}\n"
                "# HELP eklavya_http_request_duration_seconds_total Cumulative request time.\n"
                "# TYPE eklavya_http_request_duration_seconds_total counter\n"
                f"eklavya_http_request_duration_seconds_total {self.duration_seconds:.6f}\n"
            )


metrics = Metrics()


class RequestMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, configuration: Settings):
        super().__init__(app)
        self.configuration = configuration

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied = request.headers.get("x-request-id", "")
        request_id = supplied if REQUEST_ID.fullmatch(supplied) else uuid4().hex
        request.state.request_id = request_id
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = time.monotonic() - started
            metrics.observe(500, elapsed)
            logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id, "method": request.method, "path": request.url.path,
                    "status": 500, "duration_ms": round(elapsed * 1000, 2),
                },
            )
            raise
        elapsed = time.monotonic() - started
        metrics.observe(response.status_code, elapsed)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store")
        if self.configuration.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        logger.info(
            "request_complete",
            extra={
                "request_id": request_id, "method": request.method, "path": request.url.path,
                "status": response.status_code, "duration_ms": round(elapsed * 1000, 2),
            },
        )
        return response


@dataclass
class Window:
    count: int
    resets_at: float


class MemoryLimiter:
    """Development fallback; production uses Redis for cross-worker limits."""

    def __init__(self) -> None:
        self._windows: dict[str, Window] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, seconds: int, now: float | None = None) -> tuple[bool, int]:
        current = time.monotonic() if now is None else now
        with self._lock:
            window = self._windows.get(key)
            if window is None or window.resets_at <= current:
                window = Window(0, current + seconds)
                self._windows[key] = window
            window.count += 1
            return window.count <= limit, max(1, int(window.resets_at - current))


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, configuration: Settings):
        super().__init__(app)
        self.configuration = configuration
        self.redis = Redis.from_url(configuration.redis_url, decode_responses=True, socket_timeout=1)
        self.memory = MemoryLimiter()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rule = self._rule(request)
        if not self.configuration.rate_limit_enabled or rule is None:
            return await call_next(request)
        group, limit, seconds = rule
        identity = self._identity(request)
        bucket = int(time.time() // seconds)
        key = f"eklavya:rate:{group}:{identity}:{bucket}"
        try:
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, seconds + 1)
            allowed, retry_after = count <= limit, seconds - int(time.time() % seconds)
        except Exception:
            logger.exception("rate_limit_store_unavailable")
            if self.configuration.environment == "production":
                return JSONResponse(status_code=503, content={"detail": "Request protection is temporarily unavailable"})
            allowed, retry_after = self.memory.hit(key, limit, seconds)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please retry later."},
                headers={"Retry-After": str(max(1, retry_after))},
            )
        return await call_next(request)

    @staticmethod
    def _rule(request: Request) -> tuple[str, int, int] | None:
        if request.method != "POST":
            return None
        path = request.url.path
        if path.endswith((
            "/auth/login", "/auth/register", "/auth/refresh", "/auth/verify-email",
            "/auth/password-reset/request", "/auth/password-reset/confirm",
        )):
            return "authentication", 10, 60
        if path.endswith("/submissions") or path.endswith("/register"):
            return "mutation", 30, 60
        return None

    @staticmethod
    def _identity(request: Request) -> str:
        authorization = request.headers.get("authorization")
        if authorization:
            return hashlib.sha256(authorization.encode()).hexdigest()[:20]
        return request.client.host if request.client else "unknown"
