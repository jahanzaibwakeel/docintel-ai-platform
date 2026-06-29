import json
import logging
import time
from collections.abc import Callable
from uuid import uuid4

from fastapi import Request, Response

from app.core.config import get_settings
from app.core.metrics import metrics


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if settings.json_logs else logging.Formatter("%(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=level, handlers=[handler], force=True)


async def request_logging_middleware(request: Request, call_next: Callable) -> Response:
    logger = logging.getLogger("app.request")
    request_id = request.headers.get("x-request-id", uuid4().hex)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        metrics.increment(
            "docintel_http_requests",
            method=request.method,
            path=route_path,
            status_code=500,
        )
        metrics.observe(
            "docintel_http_request_duration",
            duration_ms / 1000,
            method=request.method,
            path=route_path,
            status_code=500,
        )
        logger.exception(
            "request_failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        raise
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    route = request.scope.get("route")
    route_path = getattr(route, "path", request.url.path)
    response.headers["x-request-id"] = request_id
    metrics.increment(
        "docintel_http_requests",
        method=request.method,
        path=route_path,
        status_code=response.status_code,
    )
    metrics.observe(
        "docintel_http_request_duration",
        duration_ms / 1000,
        method=request.method,
        path=route_path,
        status_code=response.status_code,
    )
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response
