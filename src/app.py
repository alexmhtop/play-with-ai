import os
import uuid
from typing import List

from contextlib import asynccontextmanager
import logging
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import metrics, trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from .auth import AuthVerifier, require_scope
from .config import get_settings
from .db import get_session, init_db
from .models import Book, CreateBook, UpdateBook
from .otel import configure_otel
from .ratelimit import TokenBucketLimiter, rate_limit_middleware
from .service import BookService

settings = get_settings()


def get_book_service(session=Depends(get_session)) -> BookService:
    return BookService(session)


auth_verifier = AuthVerifier(
    issuer=settings.keycloak_issuer,
    audience=settings.keycloak_audience,
    jwks_url=settings.jwks_url,
    allowed_algs={"RS256"},
    clock_skew_seconds=30,
)
read_access = require_scope("books:read", auth_verifier)
write_access = require_scope("books:write", auth_verifier)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        auth_verifier.jwks.get_keys()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Failed to fetch JWKS from configured url") from exc
    if settings.require_https and not settings.keycloak_issuer.startswith("https://"):
        raise RuntimeError("APP_REQUIRE_HTTPS is true but issuer is not HTTPS")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="A simple Books API secured by Keycloak with Postgres persistence.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
configure_otel(app)

allowed_origins = os.getenv("APP_CORS_ORIGINS", "").split(",") if os.getenv("APP_CORS_ORIGINS") else []
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
router_v1 = APIRouter(prefix="/api/v1", tags=["v1"])
router_v2 = APIRouter(prefix="/api/v2", tags=["v2"])


@router_v1.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


@router_v1.get("/books", response_model=List[Book], dependencies=[Depends(read_access)])
def list_books(service: BookService = Depends(get_book_service)) -> List[Book]:
    return service.list()


@router_v1.post(
    "/books",
    response_model=Book,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(write_access)],
)
def create_book(payload: CreateBook, service: BookService = Depends(get_book_service)) -> Book:
    return service.create(payload)


@router_v1.get("/books/{book_id}", response_model=Book, dependencies=[Depends(read_access)])
def get_book(book_id: int, service: BookService = Depends(get_book_service)) -> Book:
    try:
        return service.get(book_id)
    except KeyError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found") from exc


@router_v1.put(
    "/books/{book_id}",
    response_model=Book,
    dependencies=[Depends(write_access)],
)
def update_book(book_id: int, payload: UpdateBook, service: BookService = Depends(get_book_service)) -> Book:
    try:
        return service.update(book_id, payload)
    except KeyError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found") from exc


@router_v1.delete(
    "/books/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(write_access)],
)
def delete_book(book_id: int, service: BookService = Depends(get_book_service)) -> None:
    try:
        service.delete(book_id)
    except KeyError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found") from exc


@router_v2.get("/books", response_model=List[Book], dependencies=[Depends(read_access)])
def list_books_v2(service: BookService = Depends(get_book_service)) -> List[Book]:
    # Example behavior change: sorted list in v2
    return sorted(service.list(), key=lambda book: book.title.lower())


app.include_router(router_v1)
app.include_router(router_v2)


@app.middleware("http")
async def security_headers(request, call_next):
    if settings.require_https:
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        if forwarded_proto and forwarded_proto.lower() != "https":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="HTTPS required")
        if request.url.scheme != "https" and not forwarded_proto:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="HTTPS required")

    response = await call_next(request)
    response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    if request.headers.get("authorization"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


rate_limiter = TokenBucketLimiter(max_requests=1000, window_seconds=60)
app.middleware("http")(rate_limit_middleware(rate_limiter))


request_logger = logging.getLogger("books_api.requests")


@app.middleware("http")
async def request_logging_middleware(request, call_next):
    request_logger.info("request.start", extra={"path": request.url.path, "method": request.method})
    response = await call_next(request)
    request_logger.info(
        "request.end",
        extra={"path": request.url.path, "method": request.method, "status": response.status_code},
    )
    return response


@app.middleware("http")
async def request_id_middleware(request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


FastAPIInstrumentor.instrument_app(
    app,
    tracer_provider=trace.get_tracer_provider(),
    meter_provider=metrics.get_meter_provider(),
)
