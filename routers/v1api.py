from fastapi import APIRouter, Response, Request, status, Header, Depends
from fastapi.responses import RedirectResponse
from utils.debug import Debug
from pydantic import BaseModel
from dotenv import load_dotenv

import os
import json
import aiohttp
import utils.v1 as v1
from utils.http import HttpsClient
import urllib.parse

load_dotenv()
router = APIRouter(prefix="/api/v1", tags=["v1 解析端點"])
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

def send_debug_error(request: Request, error_message: str, school_name: str, page: str):
    client = getattr(request.app.state, "pb_client", None)
    Debug(client).send_error(error_message, school_name, page)


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

    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None

        return data

    url = f"{school['api']}{school['route']['merit_demerit']}"
    original_data = await http.get(url, request.cookies)
    if not original_data.data:
        send_debug_error(
            request,
            original_data.data,
            school_name,
            "merit_demerit",
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = original_data.code
        data["message"] = "Failed to fetch original data."
        data["data"] = None

        return data

    r = v1.parse_merit_demerit_records(original_data.data)

    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = r

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

    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None

        return data

    url = f"{school['api']}{school['route']['curriculum']}"
    original_data = await http.get(url, request.cookies)
    if not original_data.data:
        send_debug_error(
            request,
            original_data.data,
            school_name,
            "merit_demerit",
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = original_data.code
        data["message"] = "Failed to fetch original data."
        data["data"] = None

        return data

    r = v1.parse_weekly_curriculum(original_data.data)
    if r.get("error"):
        data = request.app.state.response
        data["code"] = 500
        data["message"] = r["error"]
        data["data"] = None

        return data

    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = r

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

    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None

        return data

    url = f"{school['api']}{school['route']['attendance']}"
    original_data = await http.get(url, request.cookies)
    if not original_data.data:
        send_debug_error(
            request,
            original_data.data,
            school_name,
            "merit_demerit",
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = original_data.code
        data["message"] = "Failed to fetch original data."
        data["data"] = None

        return data

    r = v1.parse_absence_records(original_data.data, filter_types=[])

    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = r

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
    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None

        return data

    url = f"{school['api']}{school['route']['exam_menu']}"
    original_data = await http.get(url, request.cookies)

    if not original_data.data:
        send_debug_error(
            request,
            original_data.data,
            school_name,
            "merit_demerit",
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = original_data.code
        data["message"] = "Failed to fetch original data."
        data["data"] = None

        return data

    r = v1.parse_exam_menu(original_data.data)

    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = r

    return data


@router.post("/exam_results", summary="解析考試成績")
async def get_exam_results(item: HTMLInput, request: Request, exam: str):
    """
    取得考試成績，回傳 JSON 格式的考試成績資料。
     - 需帶入 cookies
     - **返回值**: 包含學期成績資料的 JSON 物件。
    """
    r = v1.parse_exam_scores(item.html)
    if r.get("error"):
        data = request.app.state.response
        data["code"] = 500
        data["message"] = r["error"]
        data["data"] = None

        return data

    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = r

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

    if semester < 1 or semester > 3:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Invalid semester. Must be 1 ~ 3."
        data["data"] = None

        return data

    school_info = request.app.state.schools.get(school_name)
    if not school_info:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None

        return data

    year_class = ["", "一", "二", "三"][semester]
    url = f"{school_info['api']}{school_info['route']['semester_scores']}".replace(
        "{year_class}", urllib.parse.quote(year_class.encode("big5"))
    ).replace("{number}", str(semester))

    original_data = await http.get(url, request.cookies)

    if not original_data.data:
        send_debug_error(
            request,
            original_data.data,
            school_name,
            "merit_demerit",
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = 500
        data["message"] = "Failed to fetch original data."
        data["data"] = None

        return data

    r = v1.StudentGradeExtractor(original_data.data)
    r = r.get_all_grade_data()

    if r.get("error"):
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = 500
        data["message"] = r["error"]
        data["data"] = None

        return data

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = r

    return data
