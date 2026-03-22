from fastapi import APIRouter, Response, Request, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from utils.pb import *

import os
import json
import aiohttp
import utils.v1 as v1
from utils.http import HttpsClient
import urllib.parse
import pocketbase

load_dotenv()
router = APIRouter(prefix="/restaurant", tags=["吃啥？端點"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/", summary="餐廳列表")
async def index(request: Request, response: Response, school: str, page: int = 1):
    db = request.app.state.pb_client
    record = db.collection("restaurant").get_list(
        page=page, per_page=500, query_params={"filter": f'school="{school}"'}
    )
    return record


@router.get("/evaluate/{restaurant_id}", summary="餐廳評價")
async def evaluate(
    request: Request, response: Response, restaurant_id: str, page: int = 1
):
    db = request.app.state.pb_client
    record = db.collection("restaurant_evaluate").get_list(
        page=page, per_page=50, query_params={"filter": f'restaurant="{restaurant_id}"'}
    )
    return record


@router.post("/evaluate", summary="新增餐廳評價")
@limiter.limit("10/minute")
async def add_evaluate(request: Request, response: Response, item: dict):
    db = request.app.state.pb_client

    user = get_user(request.headers.get("Authorization"))
    if not user:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"code": 401, "message": "Unauthorized", "data": None}

    restaurant_id = item.get("restaurant")
    existing = db.collection("restaurant_evaluate").get_list(
        page=1, per_page=1,
        query_params={"filter": f'restaurant="{restaurant_id}"&&user="{user.id}"'}
    )
    if existing.total_items > 0:
        response.status_code = status.HTTP_409_CONFLICT
        return {"code": 409, "message": "您已評價過此餐廳", "data": None}

    record = db.collection("restaurant_evaluate").create(
        {
            "restaurant": restaurant_id,
            "evaluate": item.get("evaluate"),
            "score": item.get("score"),
            "title": item.get("title"),
            "user": user.id,
        }
    )
    return record


@router.post("/", summary="新增餐廳")
@limiter.limit("10/minute")
async def add_restaurant(request: Request, response: Response, item: dict):
    db = request.app.state.pb_client
    
    user = get_user(request.headers.get("Authorization"))
    if not user:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"code": 401, "message": "Unauthorized", "data": None}
    name = item.get("name")
    school = item.get("school")
    existing = db.collection("restaurant").get_list(
        page=1, per_page=1, query_params={"filter": f'name="{name}"&&school="{school}"'}
    )
    if existing.total_items > 0:
        response.status_code = status.HTTP_409_CONFLICT
        return {"code": 409, "message": "餐廳已存在", "data": None}
    record = db.collection("restaurant").create(
        {
            "name": name,
            "school": school,
            "map": item.get("map"),
            "user": user.id,
        }
    )
    return record

@router.delete("/{restaurant_id}", summary="刪除餐廳")
async def delete_restaurant(request: Request, response: Response, restaurant_id: str):
    db = request.app.state.pb_client
    user = get_user(request.headers.get("Authorization"))
    if not user:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"code": 401, "message": "Unauthorized", "data": None}
    record = db.collection("restaurant").get_one(restaurant_id)
    if record.user != user.id:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {"code": 403, "message": "Forbidden", "data": None}
    db.collection("restaurant").delete(restaurant_id)
    return {"code": 200, "message": "Deleted", "data": None}


@router.patch("/evaluate/{evaluate_id}", summary="更新餐廳評價")
async def update_evaluate(request: Request, response: Response, evaluate_id: str, item: dict):
    db = request.app.state.pb_client
    user = get_user(request.headers.get("Authorization"))
    if not user:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"code": 401, "message": "Unauthorized", "data": None}
    record = db.collection("restaurant_evaluate").get_one(evaluate_id)
    if record.user != user.id:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {"code": 403, "message": "Forbidden", "data": None}
    updated = {}
    for field in ["description", "score", "title"]:
        if item.get(field) is not None:
            updated[field] = item.get(field)
    if updated:
        db.collection("restaurant_evaluate").update(evaluate_id, updated)
    return {"code": 200, "message": "Updated", "data": None}