from fastapi import APIRouter, Response, Request
from fastapi.responses import RedirectResponse, FileResponse
from dotenv import load_dotenv

import os

router = APIRouter()
load_dotenv()


@router.get("/", summary="首頁")
async def index(request: Request):
    return FileResponse("templates/index.html")


@router.get("/school")
async def get_all_schools(request: Request):
    return request.app.state.schools


@router.get("/api/v{v}", summary="獲取此端點支援學校列表")
async def index(request: Request, v: int):
    """
    獲取 v2 樣式解析支援的學校列表。
     - **返回值**: 包含支援學校列表的 JSON 物件。
    """
    data = request.app.state.response
    schools = request.app.state.schools
    data["code"] = 200
    data["message"] = "Success."
    supported_schools = []
    for i in schools:
        if schools[i].get("vision") == str(f"v{v}"):
            if os.environ.get("ENV") == "production":
                if not schools[i].get("beta", False):
                    supported_schools.append(i)
            else:
                supported_schools.append(i)
    data["data"] = supported_schools

    return data
