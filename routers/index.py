from fastapi import APIRouter, Response, Request, status, Header, Depends
from fastapi.responses import RedirectResponse, FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
import aiohttp
from dotenv import load_dotenv
import utils.notice as notice
from utils import metrics as m

import os

router = APIRouter()
load_dotenv()
limiter = Limiter(key_func=get_remote_address)


def require_cookie_header(
    cookie: str = Header(
        ...,
        alias="Cookie",
        description="登入後取得的 Cookie 標頭",
    )
):
    return cookie


headers = {
    "Accept": "*/*",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


@router.get("/", summary="首頁")
async def index(request: Request):
    return FileResponse("templates/index.html")


@router.get("/privacy-policy", summary="隱私權政策")
async def privacy_policy():
    return FileResponse("templates/privacy-policy.html")


@router.get("/disclaimer", summary="免責聲明")
async def disclaimer():
    return FileResponse("templates/disclaimer.html")


@router.get("/creator-policy", summary="創作者政策")
async def creator_policy():
    return FileResponse("templates/creator-policy.html")


@router.get("/school")
async def get_all_schools(request: Request):
    return request.app.state.schools


@router.get("/me", summary="獲取使用者資訊")
async def get_me(request: Request, response: Response):
    return FileResponse("templates/me.html")


@router.get("/@{username}", summary="公開個人資料頁面")
async def get_user_profile(request: Request, username: str):
    return FileResponse("templates/user.html")

@router.get("/apply", summary="申請學校")
async def apply_school():
    return FileResponse("templates/apply.html")


@router.get("/api/v{v}", summary="獲取此端點支援學校列表")
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


@router.get("/ping", summary="檢查登入狀態")
async def ping(
    request: Request,
    response: Response,
    school_name: str,
    _cookie: str = Depends(require_cookie_header),
):
    """檢查登入狀態，回傳 JSON 格式的結果。
    - 需帶入 cookies
    - **返回值**: 包含登入狀態的 JSON 物件。
    """
    m.SCHOOL_LOGIN_CHECKS_TOTAL.labels(school_name=school_name, result="attempt").inc()
    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None

        return data

    async with aiohttp.ClientSession(
        cookies=request.cookies, headers=headers
    ) as session:

        # for v4
        query = [f"token={request.cookies.get('X-Token')}"]

        # for v5
        rd = {
            "session_key": request.cookies.get("session_key"),
        }
        url = f"{school['api']}{school['url']['logined']}?" + "&".join(query)

        for method in ["get", "post"]:
            r = await getattr(session, method)(url, data=rd)
            try:
                html = await r.text(encoding="utf-8")
            except:
                html = await r.text(encoding="big5")

            for i in school["login"]["successKeywords"]:
                if i in html:
                    m.SCHOOL_LOGIN_CHECKS_TOTAL.labels(school_name=school_name, result="logged_in").inc()
                    data["code"] = 200
                    data["message"] = "Success."
                    data["data"] = {"logged_in": True}

                    return data

    m.SCHOOL_LOGIN_CHECKS_TOTAL.labels(school_name=school_name, result="not_logged_in").inc()
    response.status_code = status.HTTP_403_FORBIDDEN
    data["code"] = 403
    data["message"] = "Success."
    data["data"] = {"logged_in": False}
    return data


@router.get("/api/v{v}/notice", summary="獲取公告列表")
async def get_notice(request: Request, v: int,school_name: str,response: Response):
    m.SCHOOL_NOTICE_REQUESTS_TOTAL.labels(school_name=school_name, api_version=f"v{v}").inc()
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
        return {"code": 404, "message": "This school does not support notice.", "data": None}
    result = await func(school['notice']['url'], method=school['notice']['method'])
    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = result

    return data


@router.post("/api/report", summary="檢舉內容")
@limiter.limit("3/minute")
async def report(request: Request, item: dict):
    db = request.app.state.pb_client

    data = {
        "restaurant": item.get("restaurant_id"),
        "restaurant_evaluate": item.get("restaurant_evaluate_id"),
        "restaurant_menu": item.get("restaurant_menu_id"),
        "reason": item["reason"],
        "description": item.get("description"),
    }

    db.collection("report").create(data)
    m.REPORT_TOTAL.inc()
    return {"code": 200, "message": "Reported", "data": None}
