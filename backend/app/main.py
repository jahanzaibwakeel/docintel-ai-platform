from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from sqlalchemy import text

from app.api.routes import admin, auth, collections, documents, notifications, saved_searches, search, workspaces
from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.core.logging import configure_logging, request_logging_middleware
from app.core.metrics import metrics
from app.core.rate_limit import rate_limit_middleware

settings = get_settings()
configure_logging()
app = FastAPI(title=settings.app_name)
app.middleware("http")(request_logging_middleware)
app.middleware("http")(rate_limit_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready(response: Response) -> dict[str, str | dict[str, str]]:
    checks: dict[str, str] = {}
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    try:
        Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2).ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
    if status != "ok":
        response.status_code = 503
    return {"status": status, "checks": checks}


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics() -> Response:
    return Response(metrics.render_prometheus(), media_type="text/plain; version=0.0.4")


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(search.router, prefix=settings.api_prefix)
app.include_router(saved_searches.router, prefix=settings.api_prefix)
app.include_router(collections.router, prefix=settings.api_prefix)
app.include_router(workspaces.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(notifications.router, prefix=settings.api_prefix)
