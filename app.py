import importlib
import pocketbase
import os

from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, Response, status

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
