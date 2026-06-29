import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request, Response
from redis import Redis
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.metrics import metrics


_local_buckets: defaultdict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _allow_local(key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    bucket = _local_buckets[key]
    while bucket and bucket[0] <= now - window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True


def _allow_redis(key: str, limit: int, window_seconds: int) -> bool:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
    count = redis.incr(key)
    if count == 1:
        redis.expire(key, window_seconds)
    return int(count) <= limit


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    settings = get_settings()
    if not settings.rate_limit_enabled or request.url.path in {"/health", "/ready", "/metrics"}:
        return await call_next(request)

    key = f"rate-limit:{_client_key(request)}:{request.url.path}"
    try:
        allowed = _allow_redis(key, settings.rate_limit_per_minute, 60)
    except Exception:
        allowed = _allow_local(key, settings.rate_limit_per_minute, 60)

    if not allowed:
        metrics.increment("docintel_rate_limited_requests", path=request.url.path)
        return JSONResponse(
            {"detail": "Too many requests. Please slow down and try again shortly."},
            status_code=429,
            headers={"Retry-After": "60"},
        )
    return await call_next(request)


def reset_local_rate_limits() -> None:
    _local_buckets.clear()
