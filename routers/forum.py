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
router = APIRouter(prefix="/api/forum", tags=["論壇"])


@router.get("/{school_name}", summary="取得文章列表")
async def get_curriculum_template(
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
            print(user_data)
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
async def get_curriculum_template(
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
            print(user_data)
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
async def get_curriculum_template(
    request: Request, response: Response, post_id
):
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
async def get_curriculum_template(
    request: Request, response: Response, post_id
):
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
