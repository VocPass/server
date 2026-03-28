import importlib
import pocketbase
import json
import os
import time
import traceback

from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, Request, Response, status, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from utils.debug import Debug
from utils.logger import log_request, log_error, log_startup, app_logger
from utils import metrics as m

load_dotenv()

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="VocPass API", description="VosPass 後端 API 文件。", version="1.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

client = pocketbase.PocketBase(os.getenv("PB_URL"))
app.state.pb_client = client

app.state.db = client.admins.auth_with_password(
    os.getenv("PB_EMAIL"), os.getenv("PB_PASSWORD")
)
app.state.response = {"code": 500, "message": "Unknow Error.", "data": None}
with open("school.json", "r", encoding="utf-8") as f:
    app.state.schools = json.load(f)

m.SCHOOLS_LOADED.set(len(app.state.schools))
version_counts: dict[str, int] = {}
for _school in app.state.schools.values():
    v = _school.get("vision", "unknown")
    version_counts[v] = version_counts.get(v, 0) + 1
for _v, _cnt in version_counts.items():
    m.SCHOOLS_BY_VERSION.labels(api_version=_v).set(_cnt)

routers_path = Path(__file__).parent / "routers"
for module_file in sorted(routers_path.glob("*.py")):
    if module_file.name.startswith("_"):
        continue
    module = importlib.import_module(f"routers.{module_file.stem}")
    if hasattr(module, "router"):
        app.include_router(module.router)


_METRICS_TOKEN = os.getenv("PROMETHEUS_METRICS_TOKEN", "")

@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint(
    response: Response,
    authorization: str | None = Header(default=None),
):
    if _METRICS_TOKEN:
        expected = f"Bearer {_METRICS_TOKEN}"
        if authorization != expected:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return Response("Unauthorized", status_code=401)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ── 請求計時 middleware ──────────────────────────────────────────────
@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    # /metrics 本身不計入業務指標
    if request.url.path == "/metrics":
        return await call_next(request)

    path = request.url.path
    method = request.method
    school_name = request.query_params.get("school_name")

    m.HTTP_REQUESTS_IN_FLIGHT.labels(method=method, path=path).inc()
    start = time.perf_counter()

    try:
        response = await call_next(request)
    finally:
        duration = time.perf_counter() - start
        m.HTTP_REQUESTS_IN_FLIGHT.labels(method=method, path=path).dec()

    status_code = response.status_code
    duration_ms = duration * 1000

    # Prometheus
    m.HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status_code=status_code).inc()
    m.HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(duration)

    content_length = response.headers.get("content-length")
    if content_length:
        m.HTTP_RESPONSE_SIZE_BYTES.labels(method=method, path=path).observe(int(content_length))

    if status_code >= 400:
        m.HTTP_ERRORS_TOTAL.labels(status_code=status_code, path=path).inc()

    # Loki
    log_request(
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        school_name=school_name,
        client_ip=request.client.host if request.client else None,
        query_params=dict(request.query_params),
    )

    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    m.HTTP_ERRORS_TOTAL.labels(
        status_code=exc.status_code, path=request.url.path
    ).inc()
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail, "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    message = errors[0]["msg"] if errors else "Validation Error."
    m.HTTP_ERRORS_TOTAL.labels(status_code=422, path=request.url.path).inc()
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": 422, "message": message, "data": None},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    error_message = "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
    school_name = request.query_params.get("school_name", "system")
    error_id = Debug(getattr(request.app.state, "pb_client", None)).send_error(
        error_message, school_name, request.url.path, 500
    )

    error_type = type(exc).__name__
    m.ERRORS_TOTAL.labels(
        school_name=school_name, error_type=error_type, path=request.url.path
    ).inc()
    log_error(
        message=str(exc),
        school_name=school_name,
        path=request.url.path,
        error_type=error_type,
        error_id=error_id,
        exc=exc,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": 500, "message": str(exc), "data": None, "error_id": error_id},
    )


@app.on_event("startup")
async def on_startup():
    log_startup(
        schools_count=len(app.state.schools),
        env=os.environ.get("APP_ENV", "development"),
    )
    app_logger.info("vocpass api ready")
