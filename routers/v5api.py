from fastapi import APIRouter, Response, Request, status, Header, Depends
from fastapi.responses import RedirectResponse
from utils.debug import Debug
from pydantic import BaseModel
from dotenv import load_dotenv

import os
import json
import aiohttp
import time
import utils.v5 as v5
from utils.base import *
from utils.http import HttpsClient
import urllib.parse

load_dotenv()
router = APIRouter(prefix="/api/v5", tags=["v5 解析端點"])
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


def send_debug_error(
    request: Request, error_message: str, school_name: str, page: str, status: int
):
    client = getattr(request.app.state, "pb_client", None)
    r = Debug(client).send_error(error_message, school_name, page, status)
    return r


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
    rd = {
        "_search": False,
        "nd": int(time.time()),
        "rows": "3000000",
        "page": "1",
        "sidx": "",
        "sord": "asc",
        "session_key": request.cookies.get("session_key"),
    }

    original_data = await http.post(url, rd, request.cookies, "utf-8")

    if not original_data.data:
        e = send_debug_error(
            request,
            original_data.data,
            school_name,
            "merit_demerit",
            original_data.code,
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = original_data.code
        data["error_id"] = e
        data["message"] = "Failed to fetch original data."
        data["data"] = None

        return data

    r = v5.parse_merit_demerit_records(original_data.data)

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

    data = request.app.state.response
    response.status_code = status.HTTP_404_NOT_FOUND
    data["code"] = 404
    data["message"] = "Not Implemented"

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

    url = f"{school['api']}{school['route']['attendance']}?dataName=vo"
    rd = {
        "_search": False,
        "nd": int(time.time()),
        "rows": "3000000",
        "page": "1",
        "sidx": "",
        "sord": "asc",
        "session_key": request.cookies.get("session_key"),
    }

    original_data = await http.post(url, rd, request.cookies, "utf-8")
    if not original_data.data:
        e = send_debug_error(
            request,
            original_data.data,
            school_name,
            "merit_demerit",
            original_data.code,
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = original_data.code
        data["error_id"] = e
        data["message"] = "Failed to fetch original data."
        data["data"] = None

        return data
    r = v5.parse_absence_records(original_data.data)

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
    original_data = await http.get(url, request.cookies, "utf-8")

    if not original_data.data:
        e = send_debug_error(
            request,
            original_data.data,
            school_name,
            "merit_demerit",
            original_data.code,
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = original_data.code
        data["error_id"] = e
        data["message"] = "Failed to fetch original data."
        data["data"] = None

        return data

    data = request.app.state.response
    response.status_code = status.HTTP_404_NOT_FOUND
    data["code"] = 404
    data["message"] = "Not Implemented"

    return data


@router.post("/exam_results", summary="解析考試成績")
async def get_exam_results(
    item: HTMLInput, request: Request, exam: str, response: Response
):
    """
    取得考試成績，回傳 JSON 格式的考試成績資料。
     - 需帶入 cookies
     - **返回值**: 包含學期成績資料的 JS
    """

    data = request.app.state.response
    response.status_code = status.HTTP_404_NOT_FOUND
    data["code"] = 404
    data["message"] = "Not Implemented"

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
    classinfo = json.loads(
        urllib.parse.unquote(request.cookies.get("openid.ext1.value.classinfo", []))
    )

    statusM = classinfo[0]["classId"]
    stdId = request.cookies.get("accountId", "")
    url = f"{school_info['api']}{school_info['route']['info']}".replace(
        "{statusM}", statusM
    ).replace("{stdId}", stdId)
    rd = {
        "_search": "false",
        "nd": int(time.time()),
        "rows": "-1",
        "page": "1",
        "sidx": "syear,seme",
        "sord": "asc",
        "session_key": request.cookies.get("session_key"),
    }

    user_info = await http.post(url, rd, request.cookies, "utf-8")
    dl = len(user_info.data["dataRows"])
    if dl < 3:
        now_year = 1
    elif dl < 5:
        now_year = 2
    else:
        now_year = 3
    si = (semester - 1) * 2
    stdSemeId = [row["id"] for row in user_info.data["dataRows"][si : si+2]]


    date = YearModel()
    syear = max(date.year - (now_year - semester), 1)
    rd = {
        "_search": "false",
        "nd": int(time.time()),
        "rows": "-1",
        "page": "1",
        "sidx": "syear desc,seme desc,itemNo",
        "sord": "asc",
        "session_key": request.cookies.get("session_key"),
    }

    all_scores_id = []
    for seme in range(1, 3):
        url = f"{school_info['api']}{school_info['route']['exam_menu']}".replace(
            "{syear}", str(syear)
        ).replace("{seme}", str(seme))
        original_data = await http.post(url, rd, request.cookies, "utf-8")
        for i in original_data.data.get("dataRows", []):
            if "學期成績" in i["name"]:
                all_scores_id.append(i["id"])
    first_semester_grades = []
    second_semester_grades = []

    for i in range(2):
        try:
            itemId=all_scores_id[i]
            ss=stdSemeId[i]
        except:
            continue
        url = f"{school_info['api']}{school_info['route']['semester_scores']}".replace(
            "{itemId}", str(itemId)
        ).replace("{stdSemeId}", str(ss))
        
        rd = {
            "_search": "false",
            "nd": int(time.time()),
            "rows": "-1",
            "page": "1",
            "sidx": "",
            "sord": "asc",
            "session_key": request.cookies.get("session_key"),
        }
        original_data = await http.post(url, rd, request.cookies, "utf-8")
        if first_semester_grades == []:
            first_semester_grades = original_data.data
        else:
            second_semester_grades = original_data.data
            
    if not original_data.data:
        e = send_debug_error(
            request,
            original_data.data,
            school_name,
            "merit_demerit",
            original_data.code,
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = 500
        data["error_id"] = e
        data["message"] = "Failed to fetch original data."
        data["data"] = None

        return data

    subject_scores = v5.parse_semester_grades(first_semester_grades, second_semester_grades)

    rows = (first_semester_grades or {}).get("dataRows", [])
    std_name = rows[0].get("stdCname", "") if rows else ""
    cls_name = user_info.data["dataRows"][-1]["clsCname"] if user_info.data.get("dataRows") else ""
    student_info = f"{std_name}│{cls_name}" if std_name and cls_name else std_name or cls_name

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = {
        "student_info": student_info,
        "subject_scores": subject_scores,
        "total_scores": {},
        "daily_performance": {},
    }

    return data
