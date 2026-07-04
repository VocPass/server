from fastapi import APIRouter, Response, Request, status, Header, Depends
from fastapi.responses import RedirectResponse, FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
import aiohttp
from utils.pb import *
from dotenv import load_dotenv
import utils.notice as notice
from utils import metrics as m


import os

router = APIRouter(prefix="/api", tags=["API 端點"])
limiter = Limiter(key_func=get_remote_address)
load_dotenv()


@router.get("/curriculum/{username}", summary="取得課表")
async def index(request: Request, username: str, response: Response):
    db = request.app.state.pb_client
    record = db.collection("users").get_first_list_item(f'username="{username}"')
    if record.curriculum_status:
        return record.curriculum
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"code": 404, "message": "Curriculum not found.", "data": None}


@router.post("/share_curriculum", summary="分享課表")
async def share_curriculum_api(
    request: Request, curriculum: dict, share_status: int, response: Response
):
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


@router.get("/developer", summary="獲取開發者資訊")
async def get_developer_info(request: Request, response: Response):
    db = request.app.state.pb_client
    od = db.collection("developer").get_full_list(query_params={"expand": "user"})
    result = []
    for i in od:
        user = i.expand["user"]
        result.append(
            {
                "user": {
                    "name": user.name,
                    "avatar": request.app.state.pb_client.get_file_url(
                        user, user.avatar
                    ),
                    "username": user.username,
                },
                "website": i.website,
                "description": i.description,
                "role": i.role,
            }
        )
    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = result
    return data


@router.get("/v{v}/notice", summary="獲取公告列表")
async def get_notice(request: Request, v: int, school_name: str, response: Response):
    m.SCHOOL_NOTICE_REQUESTS_TOTAL.labels(
        school_name=school_name, api_version=f"v{v}"
    ).inc()
    school = request.app.state.schools.get(school_name)
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"code": 400, "message": "Unsupported school.", "data": None}

    f = {"v1": notice.get_notice_v1, "v2": notice.get_notice_v2}
    func = f.get(f"v{v}")
    if not func:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"code": 404, "message": "Unsupported version.", "data": None}
    if not school.get("notice"):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {
            "code": 404,
            "message": "This school does not support notice.",
            "data": None,
        }
    result = await func(school["notice"]["url"], method=school["notice"]["method"])
    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = result

    return data


@router.post("/report", summary="檢舉內容")
@limiter.limit("3/minute")
async def report(request: Request, item: dict):
    db = request.app.state.pb_client

    data = {
        "restaurant": item.get("restaurant_id"),
        "restaurant_evaluate": item.get("restaurant_evaluate_id"),
        "restaurant_menu": item.get("restaurant_menu_id"),
        "forum_id": item.get("forum_id"),
        "forum_message_id": item.get("forum_message_id"),
        "reason": item["reason"],
        "description": item.get("description"),
    }

    db.collection("report").create(data)
    m.REPORT_TOTAL.inc()
    return {"code": 200, "message": "Reported", "data": None}


@router.get("/v{v}", summary="獲取此端點支援學校列表")
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

@router.get("/{v}/ua", summary="獲取user agent")
async def get_headers(request: Request, v: str, response: Response):
    """
    獲取 user agent。
     - **返回值**: 包含 user agent 的文字。
    """
    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3 Mobile/15E148 Safari/604.1"

    return data

@router.get("/forum_beta/{user}", summary="驗證用戶具有論壇beta資格")
async def forum_beta(request: Request, user: str, response: Response):
    """
    驗證用戶是否具有論壇beta資格。
     - **返回值**: 包含驗證結果的 JSON 物件。
    """
    db = request.app.state.pb_client
    try:
        record = db.collection("forum_beta").get_first_list_item(f'user="{user}"')
        return {"code": 200, "message": "User has forum beta access.", "data": True}
    except Exception as e:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"code": 404, "message": f"User does not have forum beta access.", "data": False}