from fastapi import APIRouter, Response, Request, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from utils.pb import *

import os
import json
import aiohttp
import utils.v1 as v1
from utils.http import HttpsClient
import urllib.parse
import pocketbase

load_dotenv()
router = APIRouter(prefix="/auth", tags=["VocPass 登入端點"])


@router.get("/", summary="Login 頁面")
async def index(request: Request, response: Response):
    return FileResponse("templates/auth.html", media_type="text/html")


@router.get("/me", summary="獲取當前用戶資訊")
async def me(request: Request):
    token = request.headers.get("Authorization")

    if token:
        user = get_user(token)
        if user:
            return user
    return Response(content="Unauthorized", status_code=status.HTTP_401_UNAUTHORIZED)
