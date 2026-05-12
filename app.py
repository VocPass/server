import importlib
import inspect
import pocketbase
import json
import os
import time

from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, Request, Response, status, Header
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse, FileResponse
from fastapi.responses import HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from utils.logger import log_request, log_error, log_startup, app_logger
from utils.debug import Debug
from utils import metrics as m

load_dotenv()

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="VocPass API",
    description="VosPass 後端 API 文件。",
    version="1.0.0",
    docs_url=None,
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


AUTH_SCHEME_NAME = "Authorization"


def _route_uses_authorization(route: APIRoute) -> bool:
    try:
        source = inspect.getsource(route.endpoint)
    except (OSError, TypeError):
        return False
    return "Authorization" in source or "authorization" in source


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes[AUTH_SCHEME_NAME] = {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": (
            "輸入 PocketBase token。可填純 token，或填 Bearer <token>；"
            "API Docs 也會嘗試從 /auth 登入後的瀏覽器儲存資料自動帶入。"
        ),
    }

    for route in app.routes:
        if not isinstance(route, APIRoute) or not _route_uses_authorization(route):
            continue

        path_schema = openapi_schema.get("paths", {}).get(route.path_format)
        if not path_schema:
            continue

        for method in route.methods or []:
            operation = path_schema.get(method.lower())
            if operation:
                operation["security"] = [{AUTH_SCHEME_NAME: []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/docs", include_in_schema=False)
async def swagger_ui_html():
    openapi_url = json.dumps(app.openapi_url)
    title = f"{app.title} - Swagger UI"
    auth_scheme_name = json.dumps(AUTH_SCHEME_NAME)

    return HTMLResponse(
        f"""
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <link rel="icon" type="image/png" href="https://github.com/vocpass.png">
    <title>{title}</title>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
    const AUTH_SCHEME_NAME = {auth_scheme_name};
    const DOCS_TOKEN_KEY = "vocpass_docs_token";

    function readStoredToken(key) {{
        const raw = window.sessionStorage.getItem(key) || window.localStorage.getItem(key);
        if (!raw) return null;
        try {{
            const value = JSON.parse(raw);
            if (typeof value === "string") return value;
            if (value && typeof value.token === "string") return value.token;
            if (value && value.auth && typeof value.auth.token === "string") return value.auth.token;
        }} catch (_) {{
            return raw;
        }}
        return null;
    }}

    function consumeTokenFromUrl() {{
        const url = new URL(window.location.href);
        const token = url.searchParams.get("token") || url.searchParams.get("authorization");
        if (!token) return null;

        window.sessionStorage.setItem(DOCS_TOKEN_KEY, token);
        url.searchParams.delete("token");
        url.searchParams.delete("authorization");
        window.history.replaceState(null, "", url.pathname + url.search + url.hash);
        return token;
    }}

    function getDocsToken() {{
        return (
            consumeTokenFromUrl() ||
            readStoredToken(DOCS_TOKEN_KEY) ||
            readStoredToken("pocketbase_auth") ||
            readStoredToken("pb_auth")
        );
    }}

    window.onload = function() {{
        window.ui = SwaggerUIBundle({{
            url: {openapi_url},
            dom_id: "#swagger-ui",
            deepLinking: true,
            persistAuthorization: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.SwaggerUIStandalonePreset
            ],
            layout: "BaseLayout",
            requestInterceptor: function(request) {{
                request.headers = request.headers || {{}};
                if (!request.headers.Authorization && !request.headers.authorization) {{
                    const token = getDocsToken();
                    if (token) request.headers.Authorization = token;
                }}
                return request;
            }},
            onComplete: function() {{
                const token = getDocsToken();
                if (token && window.ui && window.ui.preauthorizeApiKey) {{
                    window.ui.preauthorizeApiKey(AUTH_SCHEME_NAME, token);
                }}
            }}
        }});
    }};
    </script>
</body>
</html>
        """
    )


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
        status_code = response.status_code
    except Exception:
        status_code = 500
        raise
    finally:
        duration = time.perf_counter() - start
        m.HTTP_REQUESTS_IN_FLIGHT.labels(method=method, path=path).dec()
    duration_ms = duration * 1000

    # Prometheus
    m.HTTP_REQUESTS_TOTAL.labels(
        method=method, path=path, status_code=status_code
    ).inc()
    m.HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(duration)

    content_length = response.headers.get("content-length")
    if content_length:
        m.HTTP_RESPONSE_SIZE_BYTES.labels(method=method, path=path).observe(
            int(content_length)
        )

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
async def http_exception_handler(request: Request, exc: StarletteHTTPException,response: Response):
    m.HTTP_ERRORS_TOTAL.labels(status_code=exc.status_code, path=request.url.path).inc()
    school_name = request.query_params.get("school_name", "system")
    pb_client = getattr(request.app.state, "pb_client", None)
    Debug(pb_client).send_error(
        error_message=exc.detail,
        school=school_name,
        page=request.url.path,
        status=exc.status_code,
    )
    if exc.status_code == 404 and "mozilla" in request.headers.get("User-Agent", "").lower():
        return FileResponse("templates/404.html")
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail, "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    message = errors[0]["msg"] if errors else "Validation Error."
    m.HTTP_ERRORS_TOTAL.labels(status_code=422, path=request.url.path).inc()
    school_name = request.query_params.get("school_name", "system")
    pb_client = getattr(request.app.state, "pb_client", None)
    Debug(pb_client).send_error(
        error_message=message,
        school=school_name,
        page=request.url.path,
        status=422,
        traceback=str(errors),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": 422, "message": message, "data": None},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    import traceback as tb

    school_name = request.query_params.get("school_name", "system")
    error_type = type(exc).__name__
    m.ERRORS_TOTAL.labels(
        school_name=school_name, error_type=error_type, path=request.url.path
    ).inc()
    log_error(
        message=str(exc),
        school_name=school_name,
        path=request.url.path,
        error_type=error_type,
        exc=exc,
    )
    pb_client = getattr(request.app.state, "pb_client", None)
    Debug(pb_client).send_error(
        error_message=str(exc),
        school=school_name,
        page=request.url.path,
        status=500,
        traceback=tb.format_exc(),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": 500, "message": str(exc), "data": None},
    )


@app.on_event("startup")
async def on_startup():
    log_startup(
        schools_count=len(app.state.schools),
        env=os.environ.get("APP_ENV", "development"),
    )
    app_logger.info("vocpass api ready")
