from fastapi import APIRouter, Response, Request, status, Header, Depends
from fastapi.responses import RedirectResponse, FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
import aiohttp
from utils.pb import *
from dotenv import load_dotenv

import os

router = APIRouter(prefix="/api", tags=["API 端點"])
load_dotenv()


@router.get("/curriculum/{username}", summary="取得課表")
async def index(request: Request,username: str, response: Response):
    db = request.app.state.pb_client
    record = db.collection("users").get_list(
        query_params={"filter": f'username="{username}"'}
    )
    if record.items[0].curriculum_status:
        return record.items[0].curriculum
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"code": 404, "message": "Curriculum not found.", "data": None}

@router.post("/share_curriculum", summary="分享課表")
async def share_curriculum_api(request: Request, curriculum: dict, share_status: int, response: Response):
    token = request.headers.get("Authorization")
    if not token:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"code": 401, "message": "Unauthorized", "data": None}
    
    user = get_user(token)
    if not user:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"code": 401, "message": "Unauthorized", "data": None}
    
    try:
        share_curriculum(token, curriculum, share_status)
        return {"code": 200, "message": "Curriculum shared successfully.", "data": None}
    except Exception as e:
        print(f"Error sharing curriculum: {e}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"code": 500, "message": "Failed to share curriculum.", "data": None}