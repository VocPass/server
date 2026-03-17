from fastapi import APIRouter, Response, Request, status, Header, Depends
from fastapi.responses import RedirectResponse
from utils.debug import Debug
from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv

import aiohttp
import utils.v3 as v3
from utils.http import HttpsClient
from utils.base import *

load_dotenv()
router = APIRouter(prefix="/api/v3", tags=["v3 解析端點"])
http = HttpsClient()

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

    async with aiohttp.ClientSession(
        cookies=request.cookies, headers=headers
    ) as session:
        url = f"{school['api']}{school['get']['merit_demerit']}"

        r = await session.get(url)
        page_html = await r.text(encoding="utf-8")
        token = v3.get_request_verification_token(page_html)
        student_no = v3.get_query_student_no(page_html)
        if not token:

            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            data["code"] = 500
            data["message"] = "Failed to parse request verification token."
            data["data"] = None

            return data

        if not student_no:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            data["code"] = 500
            data["message"] = "Failed to parse queryStudentNo."
            data["data"] = None

            return data

        date = YearModel(datetime.now().strftime("%Y/%m/%d"))
        good = []
        bad = []
        for i in range(date.year, date.year - 4, -1):
            for j in range(1, 3):
                rd = {
                    "searchItem[Year]": str(i),
                    "searchItem[Term]": str(j),
                    "searchItem[TermInt]": "0",
                    "searchItem[TermText]": "0",
                    "searchItem[YearTermInfoFullName]": "0學年度 0",
                    "searchItem[YearTermInfoFullNameWithFullTermText]": "0學年度 0",
                    "searchItem[YearTermInfoFullNameWithChineseNumber]": "零學年度0",
                    "searchItem[YearInfoFullNameWithChineseNumber]": "零學年度",
                    "searchItem[YearTermInfoShortName]": "00",
                    "searchItem[CustomYearTermFullName]": "",
                    "searchItem[WithoutTerm]": "false",
                    "searchItem[零學年度學期對外顯示名稱]": "",
                    "searchItem[Note]": "",
                    "searchItem[Selected]": "false",
                    "searchItem[Sort]": "0",
                    "searchItem[StartDate]": "",
                    "searchItem[EndDate]": "",
                    "__RequestVerificationToken": token,
                    "studentNo": student_no,
                }

                url = f"{school['api']}{school['route']['merit_demerit']}"

                resp = await session.post(url, data=rd)
                if resp.status != 200:
                    send_debug_error(
                        request,
                        (await resp.text()),
                        school_name,
                        "merit_demerit",
                    )
                    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                    data["code"] = resp.status
                    data["message"] = "Failed to fetch original data."
                    data["data"] = None

                    return data
                original_data = await resp.json()

                r = v3.parse_merit_demerit_records(original_data)

                good.extend(r[0])
                bad.extend(r[1])

    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = [good, bad]

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
    async with aiohttp.ClientSession(
        cookies=request.cookies, headers=headers
    ) as session:
        url = f"{school['api']}{school['get']['curriculum']}"

        r = await session.get(url)
        page_html = await r.text(encoding="utf-8")
        token = v3.get_request_verification_token(page_html)

        if not token:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            data["code"] = 500
            data["message"] = "Failed to parse request verification token."
            data["data"] = None

            return data

        if r.status != 200:
            send_debug_error(
                request,
                (await r.text()),
                school_name,
                "curriculum",
            )
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            data["code"] = r.status
            data["message"] = "Failed to fetch original data."
            data["data"] = None

            return data

        date = YearModel(datetime.now().strftime("%Y/%m/%d"))
        url = f"{school['api']}{school['get']['info']}"
        r = await session.get(url)
        info_html = await r.text(encoding="utf-8")

        rd = {
            "SchoolCode": school["school_code"],
            "Year": date.year,
            "Term": date.semester,
            "WeekNo": "6",
            "ClassNo": v3.get_query_student_class(info_html),
            "ClassroomNo": "",
            "CrossName": "",
            "TeacherNo": "",
            "SubjectNo": "",
            "ShowWindow": "left",
            "TimetableType": "Class",
            "IsReverse": "false",
            "教師超鐘點顯示": "顯示",
            "教師姓名": "正常顯示",
            "學生能檢視的課程": "學生能檢視整天的課程",
            "檢視權限設定": "",
            "是否顯示午休": "隱藏",
            "是否顯示早自習": "隱藏",
            "是否顯示節次時間": "顯示",
            "顯示科目名稱": "全名",
            "是否顯示總時數": "否",
            "是否顯示實施日期": "是",
            "__RequestVerificationToken": token,
        }

        url = f"{school['api']}{school['route']['curriculum']}"

        resp = await session.post(url, data=rd)

        if resp.status != 200:
            send_debug_error(
                request,
                (await resp.text()),
                school_name,
                "curriculum",
            )
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            data["code"] = resp.status
            data["message"] = "Failed to fetch original data."
            data["data"] = None

            return data
        original_data = await resp.json()

        r = v3.parse_curriculum(original_data)

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

    all = []
    date = YearModel(datetime.now().strftime("%Y/%m/%d"))
    async with aiohttp.ClientSession(
        cookies=request.cookies, headers=headers
    ) as session:
        url = f"{school['api']}{school['get']['attendance']}"
        r = await session.get(url)
        page_html = await r.text(encoding="utf-8")
        token = v3.get_request_verification_token(page_html)
        student_no = v3.get_query_student_no(page_html)
        for i in range(1, 3):
            rd = {
                "searchItem[Year]": date.year,
                "searchItem[Term]": str(i),
                "searchItem[TermInt]": "0",
                "searchItem[TermText]": "0",
                "searchItem[YearTermInfoFullName]": "0學年度 0",
                "searchItem[YearTermInfoFullNameWithFullTermText]": "0學年度 0",
                "searchItem[YearTermInfoFullNameWithChineseNumber]": "零學年度0",
                "searchItem[YearInfoFullNameWithChineseNumber]": "零學年度",
                "searchItem[YearTermInfoShortName]": "00",
                "searchItem[CustomYearTermFullName]": "",
                "searchItem[WithoutTerm]": "false",
                "searchItem[零學年度學期對外顯示名稱]": "",
                "searchItem[Note]": "",
                "searchItem[Selected]": "false",
                "searchItem[Sort]": "0",
                "searchItem[StartDate]": "",
                "searchItem[EndDate]": "",
                "__RequestVerificationToken": token,
                "studentNo": student_no,
            }

            url = f"{school['api']}{school['route']['attendance']}"

            resp = await session.post(url, data=rd)
            if resp.status != 200:
                send_debug_error(
                    request,
                    (await resp.text()),
                    school_name,
                    "merit_demerit",
                )
                response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                data["code"] = resp.status
                data["message"] = "Failed to fetch original data."
                data["data"] = None

                return data
            original_data = await resp.json()

            r = v3.parse_absence_records(original_data, ["上", "下"][i - 1])
            all.extend(r)

    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = all

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

    school = request.app.state.schools.get(school_name)
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None

        return data

    now = datetime.now()
    date = YearModel(now.strftime("%Y/%m/%d"))
    async with aiohttp.ClientSession(
        cookies=request.cookies, headers=headers
    ) as session:
        url = f"{school['api']}{school['get']['semester_scores']}"
        r = await session.get(url)
        page_html = await r.text(encoding="utf-8")
        token = v3.get_request_verification_token(page_html)
        student_no = v3.get_query_student_no(page_html)
        rd = {
            "StudentNo": student_no,
            "SearchType": "歷年成績",
            "__RequestVerificationToken": token,
            "GradeLevel": semester,
        }

        url = f"{school['api']}{school['route']['semester_scores']}"

        resp = await session.post(url, data=rd)
        if resp.status != 200:
            send_debug_error(
                request,
                (await resp.text()),
                school_name,
                "semester_scores",
            )
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            data["code"] = resp.status
            data["message"] = "Failed to fetch original data."
            data["data"] = None

            return data
        original_data = await resp.json()

        r = v3.parse_semester_grades(original_data)

        rd = {"studentNo": student_no, "__RequestVerificationToken": token}
        url = f"{school['api']}{school['route']['daily']}"
        rp = await session.post(url, data=rd)
        daily_json = await rp.json()
        daily = v3.parse_daily_performance(daily_json, semester)
        r["daily_performance"] = daily

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = r

    return data
