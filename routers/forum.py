from fastapi import (
    APIRouter,
    Response,
    Request,
    status,
    Depends,
    UploadFile,
    File,
    Form,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse, FileResponse
from starlette.datastructures import UploadFile as StarletteUploadFile
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
router = APIRouter(prefix="/api/forum", tags=["論壇"])

tags = {"公告": {"color": "#FF0000", "admin_only": False}}


@router.get("/tags", summary="取得標籤列表")
async def get_school_post(request: Request, response: Response):
    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = tags
    return data


@router.get("/{school_name}", summary="取得文章列表")
async def get_school_post(
    request: Request, response: Response, school_name: str, page: int = 1
):
    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school and school_name != "all":
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None

        return data
    db = request.app.state.pb_client

    forums = db.collection("forum").get_list(
        page=page,
        per_page=50,
        query_params={
            "filter": (
                f'school="{sanitize_str(school_name)}"' if school_name != "all" else ""
            ),
            "expand": "user",
        },
    )

    f = []
    for forum in forums.items:
        forum_data = forum.__dict__.copy()

        if forum.anonymous:
            forum_data["user"] = None
        else:
            user_data = forum_data["expand"]["user"].__dict__.copy()
            forum_data["user"] = {
                "name": user_data["name"],
                "username": user_data["username"],
                "avatar": f"{os.environ.get('PB_URL')}api/files/_pb_users_auth_/{user_data['id']}/{user_data['avatar']}",
            }
        forum_data.pop("expand", None)
        f.append(forum_data)
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = {"forums": f, "total_pages": forums.total_pages}
    return data


@router.post("/post", summary="新增文章")
async def add_post(
    request: Request,
    response: Response,
    school: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    anonymous: bool = Form(False),
    tag: str | None = Form(None),
    pin: bool = Form(False),
    images: list[UploadFile | str] | None = File(
        default=None,
        description="最多 5 張圖片",
        json_schema_extra={
            "type": "array",
            "items": {"type": "string", "format": "binary"},
        },
    ),
):
    data = request.app.state.response
    db = request.app.state.pb_client
    token = request.headers.get("Authorization")
    user = get_user(token) if token else None
    if not user:
        response.status_code = status.HTTP_403_FORBIDDEN
        data["code"] = 403
        data["message"] = "Unauthorized."
        data["data"] = None
        return data
    if (
        (school not in request.app.state.schools) or (user.school != school)
    ) and school != "all":
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "你只能在你學校的論壇發文！"
        data["data"] = None
        return data

    try:
        if not tag:
            tag_data = []
        else:
            tag_str = tag.strip()
            if tag_str.startswith("["):
                tag_data = json.loads(tag_str)
            elif "," in tag_str:
                tag_data = [t.strip() for t in tag_str.split(",") if t.strip()]
            else:
                tag_data = [tag_str]
        if not isinstance(tag_data, list) or not all(
            isinstance(t, str) for t in tag_data
        ):
            raise ValueError("tag must be a list of strings")
    except Exception:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "tag 格式錯誤，需為字串陣列"
        data["data"] = None
        return data

    invalid_tags = [t for t in tag_data if t not in tags]
    if invalid_tags:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "tag 不存在"
        data["data"] = {"invalid_tags": invalid_tags}
        return data

    if pin or any(tags[t].get("admin_only") for t in tag_data):
        try:
            pinned_forums = db.collection("forum_admin").get_first_list_item(
                f'school="{sanitize_str(school)}"'
            )
            if user.id not in pinned_forums.admin:
                pin = False
                if any(tags[t].get("admin_only") for t in tag_data):
                    response.status_code = status.HTTP_403_FORBIDDEN
                    data["code"] = 403
                    data["message"] = "你沒有權限使用此標籤"
                    data["data"] = None
                    return data
        except:
            pin = False
            if any(tags[t].get("admin_only") for t in tag_data):
                response.status_code = status.HTTP_403_FORBIDDEN
                data["code"] = 403
                data["message"] = "你沒有權限使用此標籤"
                data["data"] = None
                return data

    image_uploads = None
    image_files = []
    for image in images or []:
        if isinstance(image, str):
            if image == "":
                continue
            response.status_code = status.HTTP_400_BAD_REQUEST
            data["code"] = 400
            data["message"] = "images 必須是檔案"
            data["data"] = None
            return data
        if not isinstance(image, StarletteUploadFile):
            response.status_code = status.HTTP_400_BAD_REQUEST
            data["code"] = 400
            data["message"] = "images 必須是檔案"
            data["data"] = None
            return data
        image_data = await image.read()
        image_files.append((image.filename, image_data, image.content_type))

    if image_files:
        if len(image_files) > 5:
            response.status_code = status.HTTP_400_BAD_REQUEST
            data["code"] = 400
            data["message"] = "圖片最多只能上傳 5 張"
            data["data"] = None
            return data
        image_uploads = FileUpload(*image_files)

    td = {}
    for t in tag_data:
        td[t] = tags[t]
    payload = {
        "user": user.id,
        "school": school,
        "title": title,
        "content": content,
        "anonymous": anonymous,
        "tag": td,
        "pin": pin,
    }
    if image_uploads:
        payload["image"] = image_uploads

    record = db.collection("forum").create(payload)

    data["code"] = 200
    data["message"] = "Success."

    return data


@router.get("/user/{user_id}", summary="取得個人文章列表")
async def get_user_post(
    request: Request, response: Response, user_id: str, page: int = 1
):
    token = request.headers.get("Authorization")
    user = get_user(token) if token else None
    data = request.app.state.response
    db = request.app.state.pb_client
    forum_filter = f'user="{sanitize_str(user_id)}"'
    if not user or user.id != user_id:
        forum_filter += " && anonymous=false"

    forums = db.collection("forum").get_list(
        page=page,
        per_page=50,
        query_params={
            "filter": forum_filter,
            "expand": "user",
        },
    )

    f = []
    for forum in forums.items:
        forum_data = forum.__dict__.copy()
        user_data = forum_data["expand"]["user"].__dict__.copy()
        forum_data["user"] = {
            "name": user_data["name"],
            "username": user_data["username"],
            "avatar": f"{os.environ.get('PB_URL')}api/files/_pb_users_auth_/{user_data['id']}/{user_data['avatar']}",
        }
        forum_data.pop("expand", None)
        f.append(forum_data)
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = {"forums": f, "total_pages": forums.total_pages}
    return data


@router.get("/post/{post_id}/message", summary="取得文章留言")
async def get_post_message(
    request: Request, response: Response, post_id, page: int = 1
):
    data = request.app.state.response
    db = request.app.state.pb_client

    forums = db.collection("forum_message").get_list(
        page=page,
        per_page=50,
        query_params={"filter": f'post="{sanitize_str(post_id)}"', "expand": "user"},
    )

    f = []
    for forum in forums.items:
        forum_data = forum.__dict__.copy()

        if forum.anonymous:
            forum_data["user"] = None
        else:
            user_data = forum_data["expand"]["user"].__dict__.copy()
            forum_data["user"] = {
                "name": user_data["name"],
                "username": user_data["username"],
                "avatar": f"{os.environ.get('PB_URL')}api/files/_pb_users_auth_/{user_data['id']}/{user_data['avatar']}",
            }
        forum_data.pop("expand", None)
        f.append(forum_data)
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = {"forums": f, "total_pages": forums.total_pages}
    return data


@router.post("/post/{post_id}/like", summary="按讚文章")
async def like_post(request: Request, response: Response, post_id):
    token = request.headers.get("Authorization")
    user = get_user(token) if token else None
    if not user:
        response.status_code = status.HTTP_403_FORBIDDEN
        data = request.app.state.response
        data["code"] = 403
        data["message"] = "Unauthorized."
        data["data"] = None
        return data

    data = request.app.state.response
    db = request.app.state.pb_client

    forums = db.collection("forum").get_first_list_item(f'id="{sanitize_str(post_id)}"')
    if user.id not in forums.likes:
        if forums.likes:
            forums.likes.append(user.id)
        else:
            forums.likes = [user.id]
        db.collection("forum").update(forums.id, {"likes": forums.likes})
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = []
    return data


@router.delete("/post/{post_id}/like", summary="取消按讚文章")
async def delike_post(request: Request, response: Response, post_id):
    token = request.headers.get("Authorization")
    user = get_user(token) if token else None
    if not user:
        response.status_code = status.HTTP_403_FORBIDDEN
        data = request.app.state.response
        data["code"] = 403
        data["message"] = "Unauthorized."
        data["data"] = None
        return data

    data = request.app.state.response
    db = request.app.state.pb_client

    forums = db.collection("forum").get_first_list_item(f'id="{sanitize_str(post_id)}"')
    if user.id in forums.likes:
        forums.likes.remove(user.id)
        db.collection("forum").update(forums.id, {"likes": forums.likes})
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = []
    return data
