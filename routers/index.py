from fastapi import APIRouter, Response, Request
from fastapi.responses import RedirectResponse, FileResponse

import utils.v1 as v1

router = APIRouter()




@router.get("/", summary="首頁")
async def index(request: Request):
   return FileResponse("templates/index.html")

@router.get("/school")
async def get_all_schools(request: Request):
    return request.app.state.schools

@router.get("/api/{v}", summary="獲取此端點支援學校列表")
async def index(request: Request,v:str = v1):
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
        if schools[i].get("vision") == str(v):
            supported_schools.append(i)
    data["data"] = supported_schools

    return data