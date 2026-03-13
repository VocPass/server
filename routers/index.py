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