from fastapi import APIRouter, Response, Request, status, Header, Depends
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import os
import json
import aiohttp
import utils.v1 as v1
from utils.http import HttpsClient
import urllib.parse

load_dotenv()
router = APIRouter(prefix="/api/demo", tags=["展示用端點"])
http = HttpsClient()


class LoginCookie(BaseModel):
    cookies: dict
    school_name: str


class HTMLInput(BaseModel):
    html: str


def require_cookie_header(
    cookie: str = Header(
        ...,
        alias="Cookie",
        description="登入後取得的 Cookie 標頭",
    )
):
    return cookie


def loder(s):
    with open(f"demo/{s}.json", "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/merit_demerit", summary="解析獎懲紀錄")
async def get_merit_demerit(
    request: Request,
    response: Response,
    school_name: str,
    _cookie: str = Depends(require_cookie_header),
):
    """
    取得獎懲紀錄的，回傳 JSON 格式的獎懲紀錄列表。
     - 需帶入 cookies
     - **返回值**: 包含學期成績資料的 JSON 物件。

    """

    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = loder(f"merit_demerit")

    return data


@router.get("/curriculum", summary="解析課表")
async def get_curriculum(
    request: Request,
    response: Response,
    school_name: str,
    _cookie: str = Depends(require_cookie_header),
):
    """
    取得課表，回傳 JSON 格式的課程表資料。
     - 需帶入 cookies
     - **返回值**: 包含學期成績資料的 JSON 物件。

    """

    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = loder(f"curriculum")

    return data


@router.get("/attendance", summary="解析出缺紀錄")
async def get_attendance(
    request: Request,
    response: Response,
    school_name: str,
    _cookie: str = Depends(require_cookie_header),
):
    """
    取得出勤紀錄，回傳 JSON 格式的出勤紀錄列表。
     - 需帶入 cookies
     - **返回值**: 包含學期成績資料的 JSON 物件。
    """

    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = loder(f"attendance")

    return data


@router.get("/exam_menu", summary="解析考試選單")
async def get_exam_menu(
    request: Request,
    response: Response,
    school_name: str,
    _cookie: str = Depends(require_cookie_header),
):
    """
    取得考試選單，回傳 JSON 格式的考試選單資料。
     - 需帶入 cookies
     - **返回值**: 包含學期成績資料的 JSON 物件。
    """

    data = request.app.state.response
    response.status_code = status.HTTP_404_NOT_FOUND
    data["code"] = 404
    data["message"] = "Not Implemented."

    return data


@router.post("/exam_results", summary="解析考試成績")
async def get_exam_results(
    item: HTMLInput, request: Request, exam: str, response: Response
):
    """
    取得考試成績，回傳 JSON 格式的考試成績資料。
     - 需帶入 cookies
     - **返回值**: 包含學期成績資料的 JSON 物件。
    """

    data = request.app.state.response
    response.status_code = status.HTTP_404_NOT_FOUND
    data["code"] = 404
    data["message"] = "Not Implemented."

    return data


@router.get("/semester_scores", summary="解析學期成績")
async def get_semester_scores(
    response: Response,
    request: Request,
    school_name: str,
    semester: int = 1,
    _cookie: str = Depends(require_cookie_header),
):
    """
    取得學期成績，回傳 JSON 格式的學期成績資料。
     - 需帶入 cookies
     - **返回值**: 包含學期成績資料的 JSON 物件。
    """
    data = request.app.state.response

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = loder(f"semester_scores")

    return data


@router.post("/login", summary="模擬登入，回傳 Cookie")
async def login(request: Request, response: Response):
    """
    模擬登入，回傳 Cookie。
     - **返回值**: 包含模擬登入後 Cookie 的 JSON 物件。
    """
    html = "done"
    # 設定模擬的 Cookie 值
    response.set_cookie(
        key="sessionid", value="fake-session-id-for-demo", httponly=True, max_age=3600
    )
    return html


@router.get("/login", summary="模擬登入")
async def login():
    return FileResponse("templates/login.html")
