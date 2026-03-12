import importlib
import pocketbase
import os

from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

load_dotenv()

app = FastAPI(
    title="VocPass API", description="VosPass 後端 API 文件。", version="1.0.0"
)

client = pocketbase.PocketBase(os.getenv("PB_URL"))

app.state.db = client.admins.auth_with_password(
    os.getenv("PB_EMAIL"), os.getenv("PB_PASSWORD")
)
app.state.response = {"code": 500, "message": "Server Error.", "data": None}

routers_path = Path(__file__).parent / "routers"
for module_file in sorted(routers_path.glob("*.py")):
    if module_file.name.startswith("_"):
        continue
    module = importlib.import_module(f"routers.{module_file.stem}")
    if hasattr(module, "router"):
        app.include_router(module.router)


@app.get("/", summary="首頁")
async def root(response: Response):
    return "Hello, VocPass API is running! Visit /docs for API documentation."


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail, "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    message = errors[0]["msg"] if errors else "Validation Error."
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": 422, "message": message, "data": None},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": 500, "message": "Internal Server Error.", "data": None},
    )
