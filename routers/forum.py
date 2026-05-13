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
from utils.send_notification import send_notification

load_dotenv()
router = APIRouter(prefix="/api/forum", tags=["論壇"])

tags = { 
    "問題": {"color": "#2563EB", "admin_only": False},
    "閒聊": {"color": "#22C55E", "admin_only": False},
    "心得": {"color": "#F59E0B", "admin_only": False},
    "活動": {"color": "#A855F7", "admin_only": False},
    "徵人": {"color": "#14B8A6", "admin_only": False},
    "失物招領": {"color": "#EF4444", "admin_only": False},
    "課業": {"color": "#6366F1", "admin_only": False},
    "社團": {"color": "#EC4899", "admin_only": False},
    "交易": {"color": "#84CC16", "admin_only": False},
    "公告": {"color": "#FF0000", "admin_only": True},
    "處理中": {"color": "#000000", "admin_only": True},
    "已完成": {"color": "#6B7280", "admin_only": True},
}


def parse_tag_names(value):
    if not value:
        return []
    if isinstance(value, dict):
        return [str(tag).strip() for tag in value.keys() if str(tag).strip()]
    if isinstance(value, list):
        return [str(tag).strip() for tag in value if str(tag).strip()]

    tag_str = str(value).strip()
    if not tag_str:
        return []
    if tag_str.startswith("["):
        parsed = json.loads(tag_str)
        if not isinstance(parsed, list):
            raise ValueError("tag must be a list of strings")
        return [str(tag).strip() for tag in parsed if str(tag).strip()]
    return [tag.strip() for tag in tag_str.split(",") if tag.strip()]


def serialize_forum_tags(value):
    tag_names = parse_tag_names(value)
    return {tag: tags.get(tag, {}) for tag in tag_names}


def relation_id(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return relation_id(value[0]) if value else None
    if isinstance(value, dict):
        return value.get("id")
    return getattr(value, "id", value)


def serialize_forum_post(forum):
    forum_data = forum.__dict__.copy()
    image_names = forum_data.get("image") or []
    if isinstance(image_names, str):
        image_names = [image_names] if image_names else []
    collection = forum_data.get("collection_id") or forum_data.get("collection_name") or "forum"
    forum_data["images"] = [
        f"{os.environ.get('PB_URL')}api/files/{collection}/{forum_data['id']}/{image}"
        for image in image_names
        if image
    ]
    forum_data["tag"] = serialize_forum_tags(forum_data.get("tag"))
    forum_data.pop("image", None)
    return forum_data


@router.get("/tags", summary="取得標籤列表")
async def get_school_post(request: Request, response: Response):
    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = tags
    return data


@router.get("/{school_name}/admin", summary="取得學校版主")
async def get_school_admin(request: Request, response: Response, school_name: str):
    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school and school_name not in  ["all","vocpass"]:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None

        return data
    db = request.app.state.pb_client

    try:
        admins = db.collection("forum_admin").get_first_list_item(
            f'school="{sanitize_str(school_name)}"'
        )
        admins.icon = (
            f"{os.environ.get('PB_URL')}api/files/pbc_1619757269/{admins.id}/{admins.icon}"
            if admins and admins.icon
            else None
        )
    except:
        admins = None
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = admins
    return data


@router.get("/{school_name}", summary="取得文章列表")
async def get_school_post(
    request: Request, response: Response, school_name: str, page: int = 1, search: str | None = None
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
            "sort": "-created" if school_name == "all" else "-pin,-created",
        },
    )

    f = []
    for forum in forums.items:
        forum_data = serialize_forum_post(forum)

        if forum.anonymous:
            forum_data["user"] = None
        else:
            user_data = forum_data["expand"]["user"].__dict__.copy()
            forum_data["user"] = {
                "id": user_data["id"],
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
        data["message"] = "你需要登入VocPass帳號才能操作。"
        data["data"] = None
        return data
    if (
        (school not in request.app.state.schools) or (user.school != school)
    ) and school != "all":
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "你只能在你學校的論壇發文，或是您未驗證你的學校。"
        data["data"] = None
        return data

    try:
        tag_data = parse_tag_names(tag)
    except Exception:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "tag 格式錯誤，需為 tag1,tag2,tag3"
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

    payload = {
        "user": user.id,
        "school": school,
        "title": title,
        "content": content,
        "anonymous": anonymous,
        "tag": ",".join(tag_data),
        "pin": pin,
    }
    if image_uploads:
        payload["image"] = image_uploads

    record = db.collection("forum").create(payload)

    data["code"] = 200
    data["message"] = "Success."

    return data

@router.delete("/post/{post_id}", summary="刪除文章")
async def delete_post(request: Request, response: Response, post_id):
    token = request.headers.get("Authorization")
    user = get_user(token) if token else None
    if not user:
        response.status_code = status.HTTP_403_FORBIDDEN
        data = request.app.state.response
        data["code"] = 403
        data["message"] = "你需要登入VocPass帳號才能操作。"
        data["data"] = None
        return data

    data = request.app.state.response
    db = request.app.state.pb_client

    forums = db.collection("forum").get_first_list_item(f'id="{sanitize_str(post_id)}"')
    if relation_id(forums.user) != user.id:
        response.status_code = status.HTTP_403_FORBIDDEN
        data["code"] = 403
        data["message"] = "You can only delete your own post."
        data["data"] = None
        return data

    db.collection("forum").delete(forums.id)
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = []

    return data


@router.get("/user/{user_id}", summary="取得個人文章列表")
async def get_user_post(
    request: Request, response: Response, user_id: str, page: int = 1
):
    token = request.headers.get("Authorization")
    user = get_user(token) if token else None
    data = request.app.state.response
    db = request.app.state.pb_client
    if user_id == "me":
        user_id = user.id if user else None
    forum_filter = f'user="{sanitize_str(user_id)}"'
    if not user or user.id != user_id:
        forum_filter += " && anonymous=false"

    forums = db.collection("forum").get_list(
        page=page,
        per_page=50,
        query_params={
            "filter": forum_filter,
            "expand": "user",
            "sort": "-created",
        },
    )

    f = []
    for forum in forums.items:
        forum_data = serialize_forum_post(forum)
        user_data = forum_data["expand"]["user"].__dict__.copy()
        forum_data["user"] = {
            "id": user_data["id"],
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
        query_params={
            "filter": f'post="{sanitize_str(post_id)}"',
            "expand": "user",
            "sort": "created",
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
                "id": user_data["id"],
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

@router.post("/post/{post_id}/message", summary="新增文章留言")
async def add_post_message(
    request: Request,
    response: Response,
    post_id: str,
    content: str = Form(...),
    anonymous: bool = Form(False),
):
    token = request.headers.get("Authorization")
    user = get_user(token) if token else None
    data = request.app.state.response
    db = request.app.state.pb_client
    if not user:
        response.status_code = status.HTTP_403_FORBIDDEN
        data["code"] = 403
        data["message"] = "你需要登入VocPass帳號才能操作。"
        data["data"] = None
        return data

    try:
        post=db.collection("forum").get_one(sanitize_str(post_id))
    except:
        response.status_code = status.HTTP_404_NOT_FOUND
        data["code"] = 404
        data["message"] = "Post not found."
        data["data"] = None
        return data

    payload = {
        "user": user.id,
        "post": post_id,
        "content": content,
        "anonymous": anonymous,
    }

    if user.school != post.school and post.school != "all":
        response.status_code = status.HTTP_403_FORBIDDEN
        data["code"] = 403
        data["message"] = "你只能在你學校的論壇留言，或是您未驗證你的學校。"
        data["data"] = None
        return data
    db.collection("forum_message").create(payload)
    if post.user != user.id:
        devices = db.collection("notify").get_full_list(
            query_params={"filter": f'user="{sanitize_str(post.user)}"'}
        )
        
        for i in devices:
            await send_notification(
                title=f"你的貼文有新留言！",
                body=f"{content[:50]}...",
                apns_token=i.apns_token,
            )

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = []
    return data

@router.delete("/message/{message_id}", summary="刪除文章留言")
async def delete_post_message(request: Request, response: Response, message_id):
    token = request.headers.get("Authorization")
    user = get_user(token) if token else None
    data = request.app.state.response
    db = request.app.state.pb_client
    if not user:
        response.status_code = status.HTTP_403_FORBIDDEN
        data["code"] = 403
        data["message"] = "你需要登入VocPass帳號才能操作。"
        data["data"] = None
        return data

    forums = db.collection("forum_message").get_one(sanitize_str(message_id))
    if relation_id(forums.user) != user.id:
        response.status_code = status.HTTP_403_FORBIDDEN
        data["code"] = 403
        data["message"] = "You can only delete your own message."
        data["data"] = None
        return data

    db.collection("forum_message").delete(forums.id)
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = []
    return data

@router.post("/post/{post_id}/like", summary="按讚文章")
async def like_post(request: Request, response: Response, post_id):
    token = request.headers.get("Authorization")
    user = get_user(token) if token else None
    if not user:
        response.status_code = status.HTTP_403_FORBIDDEN
        data = request.app.state.response
        data["code"] = 403
        data["message"] = "你需要登入VocPass帳號才能操作。"
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
        data["message"] = "你需要登入VocPass帳號才能操作。"
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


@router.post("/message/{message_id}/like", summary="按讚留言")
async def like_message(request: Request, response: Response, message_id):
    token = request.headers.get("Authorization")
    user = get_user(token) if token else None
    if not user:
        response.status_code = status.HTTP_403_FORBIDDEN
        data = request.app.state.response
        data["code"] = 403
        data["message"] = "你需要登入VocPass帳號才能操作。"
        data["data"] = None
        return data

    data = request.app.state.response
    db = request.app.state.pb_client

    forums = db.collection("forum_message").get_one(sanitize_str(message_id))
    if user.id not in forums.likes:
        if forums.likes:
            forums.likes.append(user.id)
        else:
            forums.likes = [user.id]
        db.collection("forum_message").update(forums.id, {"likes": forums.likes})
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = []
    return data

@router.delete("/message/{message_id}/like", summary="取消按讚留言")
async def delike_message(request: Request, response: Response, message_id):
    token = request.headers.get("Authorization")
    user = get_user(token) if token else None
    if not user:
        response.status_code = status.HTTP_403_FORBIDDEN
        data = request.app.state.response
        data["code"] = 403
        data["message"] = "你需要登入VocPass帳號才能操作。"
        data["data"] = None
        return data

    data = request.app.state.response
    db = request.app.state.pb_client

    forums = db.collection("forum_message").get_one(sanitize_str(message_id))
    if user.id in forums.likes:
        forums.likes.remove(user.id)
        db.collection("forum_message").update(forums.id, {"likes": forums.likes})
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = []
    return data
