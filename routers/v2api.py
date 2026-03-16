from fastapi import APIRouter, Response, Request, status, Header, Depends
from fastapi.responses import RedirectResponse
from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv

import os
import json
import aiohttp
import utils.v2 as v2
from utils.http import HttpsClient
from utils.base import *
import urllib.parse

load_dotenv()
router = APIRouter(prefix="/api/v2", tags=["v2 解析端點"])
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
    find_all = []
    url = f"{school['api']}{school['get']['merit_demerit']}"
    await http.get(url, request.cookies, "utf-8")
    for i in range(0, 3):
        for j in range(1, 3):
            now = datetime.now()

            date = YearModel(now.strftime("%Y/%m/%d"))
            year = date.year - i
            url = f"{school['api']}{school['route']['merit_demerit']}"
            search = {
                "J_Year": year,
                "J_Semi": date.semester,
                "J_StuID": "",
            }
            original_data = await http.post(url, search, request.cookies, "utf-8")
            if not original_data.data:
                response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                data["code"] = original_data.code
                data["message"] = "Failed to fetch original data."
                data["data"] = None

                return data
            r = v2.parse_merit_demerit_records(original_data.data)
            find_all.extend(r[0])

    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = find_all
    
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
    now = datetime.now()
    date = YearModel(now.strftime("%Y/%m/%d"))
    url = f"{school['api']}{school['get']['curriculum']}"
    r = await http.get(url, request.cookies, "utf-8")

    url = f"{school['api']}{school['route']['curriculum']}"
    search = {
        "ppYear": date.year,
        "ppSemi": date.semester,
    }

    original_data = await http.post(url, search, request.cookies, "utf-8")

    if not original_data.data:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = original_data.code
        data["message"] = "Failed to fetch original data."
        data["data"] = None

        return data
    
    r = v2.parse_curriculum(original_data.data,school)
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
    
    data["code"] = 404
    data["message"] = "Not Implemented."
    data["data"] = None

    return data
    url = f"{school['api']}{school['get']['attendance']}"
    r = await http.get(url, request.cookies, "utf-8")

    token = v2.get_request_verification_token(r.data)
    url = f"{school['api']}{school['route']['attendance']}"

    now = datetime.now()
    start = datetime(now.year - 3, 1, 1)

    search = {
        "__RequestVerificationToken": token,
        "StuName": "",
        "StuId": "",
        "BegDate": start.strftime("%Y/%m/%d"),
        "EndDate": now.strftime("%Y/%m/%d"),
        "SubmitButton": "查詢",
    }

    original_data = await http.post(url, search, request.cookies, "utf-8")
    if not original_data.data:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = original_data.code
        data["message"] = "Failed to fetch original data."
        data["data"] = None

        return data
    print(original_data.data)
    r = v2.parse_absence_records(original_data.data)

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

    response.status_code = status.HTTP_404_NOT_FOUND
    data = request.app.state.response
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

    now = datetime.now()
    date = YearModel(now.strftime("%Y/%m/%d"))
    # 現在年級
    s = {
        "J_Year": date.year,
        "J_Semi": "1",
        "J_StuID": "",
    }
    url = f"{school_info['api']}{school_info['route']['merit_demerit']}"

    d = await http.post(url, s, request.cookies, "utf-8")
    if not d.data:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = 500
        data["message"] = "Failed to fetch original data."
        data["data"] = None
        return data
    y = v2.parse_grade_level(d.data)

    url = f"{school_info['api']}{school_info['get']['semester_scores']}"
    await http.get(url, request.cookies, "utf-8")

    url = f"{school_info['api']}{school_info['route']['semester_scores']}"
    s1 = {
        "J_Year": max(date.year - (y - semester), 1),
        "J_Semi": "1",
        "J_StuID": "",
    }

    s2 = {
        "J_Year": max(date.year - (y - semester), 1),
        "J_Semi": "2",
        "J_StuID": "",
    }

    data1 = await http.post(url, s1, request.cookies, "utf-8")
    data2 = await http.post(url, s2, request.cookies, "utf-8")

    if not data1.data or not data2.data:

        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = 500
        data["message"] = "Failed to fetch original data."
        data["data"] = None

        return data

    r = v2.parse_semester_grades(data1.data, data2.data)

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
