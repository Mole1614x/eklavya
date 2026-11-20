import hashlib
import json
import logging
import threading
import time
from functools import lru_cache

from redis import Redis

from .config import settings

logger = logging.getLogger(__name__)
_local: dict[str, tuple[float, object]] = {}
_local_lock = threading.Lock()
_LOCAL_SECONDS = 1.0


@lru_cache
def _client(redis_url: str) -> Redis:
    return Redis.from_url(
        redis_url, socket_connect_timeout=0.05, socket_timeout=0.05,
        max_connections=50, health_check_interval=30,
    )


def cache_key(namespace: str, *parts: object) -> str:
    digest = hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()
    return f"eklavya:public:{namespace}:{digest}"


def get_public(key: str):
    if settings().public_cache_seconds <= 0:
        return None
    now = time.monotonic()
    with _local_lock:
        local = _local.get(key)
        if local is not None and local[0] > now:
            return local[1]
        _local.pop(key, None)
    client = _client(settings().redis_url)
    try:
        value = client.get(key)
        parsed = json.loads(value) if value else None
        if parsed is not None:
            with _local_lock:
                _local[key] = (now + _LOCAL_SECONDS, parsed)
        return parsed
    except Exception:
        return None


def set_public(key: str, value) -> None:
    if settings().public_cache_seconds <= 0:
        return
    client = _client(settings().redis_url)
    with _local_lock:
        _local[key] = (time.monotonic() + _LOCAL_SECONDS, value)
    try:
        client.set(key, json.dumps(value, default=str), ex=settings().public_cache_seconds)
    except Exception:
        logger.debug("public_cache_write_failed", exc_info=True)


def invalidate_public(*namespaces: str) -> None:
    prefixes = tuple(f"eklavya:public:{namespace}:" for namespace in namespaces)
    with _local_lock:
        for key in [item for item in _local if item.startswith(prefixes)]:
            _local.pop(key, None)
    client = _client(settings().redis_url)
    try:
        for namespace in namespaces:
            keys = list(client.scan_iter(match=f"eklavya:public:{namespace}:*", count=100))
            if keys:
                client.delete(*keys)
    except Exception:
        logger.debug("public_cache_invalidation_failed", exc_info=True)
