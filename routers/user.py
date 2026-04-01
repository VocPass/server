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
from utils.http_client import HttpsClient
import urllib.parse
import pocketbase
from pocketbase.models import FileUpload

load_dotenv()
router = APIRouter(prefix="/api/user", tags=["VocPass 使用者"])

@router.get("/{user}",summary="獲取使用者資訊")
async def api_get_user(request: Request, user: str,response: Response):
    """
    根據使用者 ID 或使用者名稱獲取使用者資訊。
    """
    data = request.app.state.response
    pb_client = request.app.state.pb_client
    try:
        record = pb_client.collection("users").get_first_list_item(f'id = "{user}" || username = "{user}"')
        data["code"] = 200
        data["message"] = "Success."
        data["data"] = {
            "id": record.id,
            "name": record.name,
            "username": record.username,
            "avatar": pb_client.get_file_url(record, record.avatar),
            "curriculum_status": record.curriculum_status,
        }
        if record.curriculum_status:
            data["data"]["curriculum"] = record.curriculum
        return data
    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        data["code"] = 404
        data["message"] = "User not found."
        data["data"] = None
        return data

@router.patch("/",summary="更新使用者資訊")
async def update_user(request: Request, response: Response):
    token = request.headers.get("Authorization")
    db = request.app.state.pb_client
    data = request.app.state.response
    if not token:
        return Response(content="Unauthorized", status_code=status.HTTP_401_UNAUTHORIZED)
    user_info = get_user(token)
    if not user_info:
        return Response(content="Unauthorized", status_code=status.HTTP_401_UNAUTHORIZED)
    
    form = await request.form()
    upload_data = {}
    if "name" in form:
        upload_data["name"] = form["name"]
    if "username" in form:
        try:
            other = db.collection("users").get_first_list_item(f'username="{form["username"]}" && id != "{user_info.id}"')
            response.status_code = status.HTTP_400_BAD_REQUEST
            data["code"] = 400
            data["message"] = "Username already exists."
            data["data"] = None
            return data
        except:
            upload_data["username"] = form["username"]

    if "avatar" in form:
        avatar_file = form["avatar"]
        avatar_data = await avatar_file.read()
        upload_data["avatar"] = FileUpload((avatar_file.filename, avatar_data, avatar_file.content_type))
    
    db.collection("users").update(user_info.id, upload_data)
    data["code"] = 200
    data["message"] = "User updated successfully."
    data["data"] = None
    return data


class APNsToken(BaseModel):
    device_token: str
    start_token: str=None
    update_token: str=None
    is_dev: bool=False
    is_open: bool=True
    valid: bool=True
    curriculum: dict=None

    def dict(self, **kwargs):
        data = super().dict(**kwargs)
        return data


@router.post("/notify/ios",summary="上傳Push Token")
async def upload_push_token(request: Request, item: APNsToken):
    user_token = request.headers.get("Authorization")
    db = request.app.state.pb_client
    data = item.dict()
    if user_token:
        user_info = get_user(user_token)
        if not user_info:
            return Response(content="Unauthorized", status_code=status.HTTP_401_UNAUTHORIZED)
        data['user'] = user_info.id
    data['type'] = "ios"
    try:
        old_token = db.collection("notify").get_first_list_item(f'device_token="{item.device_token}"')
        db.collection("notify").update(old_token.id, data)
    
    except:
        db.collection("notify").create(item.dict())
        
        
    return {"code": 200, "message": "Token uploaded successfully.", "data": None}