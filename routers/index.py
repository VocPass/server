from fastapi import APIRouter, Response, Request, status, Header, Depends
from fastapi.responses import RedirectResponse, FileResponse
import aiohttp
from dotenv import load_dotenv
import urllib.parse

import os

router = APIRouter()
load_dotenv()


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


@router.get("/school")
async def get_all_schools(request: Request):
    return request.app.state.schools


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
    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None

        return data

    if school.get("vision") == "v6":
        user_session = request.cookies.get("user_session")
        if not user_session:
            response.status_code = status.HTTP_403_FORBIDDEN
            data["code"] = 403
            data["message"] = "Success."
            data["data"] = {"logged_in": False}
            return data
        url = (
            f"{school['api']}/api/public/user-info?"
            f"user_session={urllib.parse.quote(user_session, safe='')}"
        )
        async with aiohttp.ClientSession(
            cookies=request.cookies, headers=headers
        ) as session:
            r = await session.get(url)
            if r.status == 200:
                try:
                    j = await r.json()
                except Exception:
                    j = None
                if isinstance(j, dict) and j.get("success"):
                    data["code"] = 200
                    data["message"] = "Success."
                    data["data"] = {"logged_in": True}
                    return data
        response.status_code = status.HTTP_403_FORBIDDEN
        data["code"] = 403
        data["message"] = "Success."
        data["data"] = {"logged_in": False}
        return data

    async with aiohttp.ClientSession(
        cookies=request.cookies, headers=headers
    ) as session:
        
        #for v4
        query=[f"token={request.cookies.get('X-Token')}"]

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
                    data["code"] = 200
                    data["message"] = "Success."
                    data["data"] = {"logged_in": True}

                    return data

    response.status_code = status.HTTP_403_FORBIDDEN
    data["code"] = 403
    data["message"] = "Success."
    data["data"] = {"logged_in": False}
    return data
