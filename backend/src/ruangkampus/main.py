import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ruangkampus.config import get_settings
from ruangkampus.database import SessionLocal, engine
from ruangkampus.rate_limit import limiter
from ruangkampus.responses import failure, success
from ruangkampus.routers import auth, dashboard, notifications, reservations, rooms, schedule_imports, schedules, users


class JsonLogFormatter(logging.Formatter):
    """Structured JSON logs; never serializes request payloads or exception messages."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        exception_type = getattr(record, "exception_type", None)
        if exception_type:
            payload["exception_type"] = exception_type
        return json.dumps(payload, ensure_ascii=False)


handler = logging.StreamHandler()
handler.setFormatter(JsonLogFormatter())
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)
logger = logging.getLogger("ruangkampus")
settings = get_settings()
MAX_REQUEST_BYTES = 6 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema creation/migration is an explicit operator/CI step, never per worker startup.
    yield
    engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="1.1.0",
    description="Backend API for RuangKampus room discovery and reservation management.",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def add_security_headers_and_request_limit(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_REQUEST_BYTES:
        return JSONResponse(status_code=413, content=failure("Request body is too large"))

    # Also count streamed/chunked bodies that omit Content-Length.
    if request.method in {"POST", "PUT", "PATCH"}:
        body_parts: list[bytes] = []
        received = 0
        async for part in request.stream():
            received += len(part)
            if received > MAX_REQUEST_BYTES:
                return JSONResponse(status_code=413, content=failure("Request body is too large"))
            body_parts.append(part)
        request._body = b"".join(body_parts)

    rate_limits = {
        (f"{settings.api_v1_prefix}/auth/login", "POST"): 5,
        (f"{settings.api_v1_prefix}/auth/register", "POST"): 5,
        (f"{settings.api_v1_prefix}/auth/forgot-password", "POST"): 3,
        (f"{settings.api_v1_prefix}/auth/reset-password", "POST"): 5,
        (f"{settings.api_v1_prefix}/auth/refresh", "POST"): 10,
    }
    limit = rate_limits.get((request.url.path, request.method))
    if limit:
        client_ip = request.client.host if request.client else "unknown"
        allowed, retry_after = limiter.check(f"{client_ip}:{request.url.path}", limit)
        if not allowed:
            response = JSONResponse(
                status_code=429,
                content=failure("Too many requests. Please try again later."),
                headers={"Retry-After": str(retry_after)},
            )
            _apply_security_headers(response)
            return response

    response = await call_next(request)
    _apply_security_headers(response)
    return response


def _apply_security_headers(response) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if settings.is_production:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request could not be completed"
    return JSONResponse(status_code=exc.status_code, content=failure(message), headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for item in exc.errors():
        errors.append({
            "code": "VALIDATION_ERROR",
            "field": ".".join(str(part) for part in item.get("loc", []) if part != "body"),
            "message": item.get("msg", "Invalid value"),
        })
    return JSONResponse(status_code=422, content=failure("Request validation failed", errors))


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    logger.info("Database integrity constraint rejected a request")
    return JSONResponse(status_code=409, content=failure("The requested change conflicts with existing data"))


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error("Database operation failed (exception_type=%s)", type(exc).__name__)
    return JSONResponse(status_code=500, content=failure("A database error occurred"))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled application error (exception_type=%s)", type(exc).__name__)
    return JSONResponse(status_code=500, content=failure("An unexpected server error occurred"))


api = settings.api_v1_prefix
app.include_router(auth.router, prefix=api)
app.include_router(users.router, prefix=api)
app.include_router(rooms.router, prefix=api)
app.include_router(reservations.router, prefix=api)
app.include_router(schedules.router, prefix=api)
app.include_router(schedule_imports.router, prefix=api)
app.include_router(notifications.router, prefix=api)
app.include_router(dashboard.router, prefix=api)


@app.get("/health", tags=["Operations"])
def health():
    # Liveness: process is running. Database readiness is reported separately.
    return success({"status": "ok"}, "Service is healthy")


@app.get("/ready", tags=["Operations"])
def ready():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return success({"status": "ready", "database": "reachable"}, "Service is ready")
    except SQLAlchemyError as exc:
        logger.error("Readiness check failed (exception_type=%s)", type(exc).__name__)
        return JSONResponse(status_code=503, content=failure("Service is not ready"))
    finally:
        db.close()
