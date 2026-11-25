import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ruangkampus.config import get_settings
from ruangkampus.database import SessionLocal
from ruangkampus.rate_limit import limiter
from ruangkampus.responses import failure, success
from ruangkampus.routers import auth, dashboard, notifications, reservations, rooms, schedules, users

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("ruangkampus")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema creation is intentionally not automatic. Apply reviewed Alembic migrations explicitly.
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
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
    if content_length and content_length.isdigit() and int(content_length) > 2 * 1024 * 1024:
        return JSONResponse(status_code=413, content=failure("Request body is too large"))
    rate_limits = {
        ("/api/v1/auth/login", "POST"): 5,
        ("/api/v1/auth/register", "POST"): 5,
        ("/api/v1/auth/forgot-password", "POST"): 3,
        ("/api/v1/auth/reset-password", "POST"): 5,
        ("/api/v1/auth/refresh", "POST"): 10,
    }
    limit = rate_limits.get((request.url.path, request.method))
    if limit:
        client_ip = request.client.host if request.client else "unknown"
        allowed, retry_after = limiter.check(f"{client_ip}:{request.url.path}", limit)
        if not allowed:
            return JSONResponse(status_code=429, content=failure("Too many requests. Please try again later."), headers={"Retry-After": str(retry_after)})
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


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
    logger.exception("Database operation failed")
    return JSONResponse(status_code=500, content=failure("A database error occurred"))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled application error")
    return JSONResponse(status_code=500, content=failure("An unexpected server error occurred"))


api = settings.api_v1_prefix
app.include_router(auth.router, prefix=api)
app.include_router(users.router, prefix=api)
app.include_router(rooms.router, prefix=api)
app.include_router(reservations.router, prefix=api)
app.include_router(schedules.router, prefix=api)
app.include_router(notifications.router, prefix=api)
app.include_router(dashboard.router, prefix=api)


@app.get("/health", tags=["Operations"])
def health():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return success({"status": "ok", "database": "reachable"}, "Service is healthy")
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content=failure("Database is unavailable"))
    finally:
        db.close()
