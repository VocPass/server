from fastapi import APIRouter, Response, Request, status, Header, Depends
from utils.debug import Debug
from pydantic import BaseModel
from dotenv import load_dotenv

import base64
import aiohttp
import utils.v8 as v8
from utils import metrics as m
from utils.base import YearModel
from urllib.parse import unquote_plus

load_dotenv()
router = APIRouter(prefix="/api/v8", tags=["v8 解析端點"])


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


def send_debug_error(request: Request, error_message: str, school_name: str, page: str, status: int, response_body=None, traceback=None):
    client = getattr(request.app.state, "pb_client", None)
    return Debug(client).send_error(error_message, school_name, page, status, response_body=response_body, traceback=traceback)


HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

NAV_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


def merge_cookies(raw_cookie_header: str, response_cookies) -> str:
    original = {
        k.strip(): v.strip()
        for part in raw_cookie_header.split(";") if "=" in part
        for k, v in [part.split("=", 1)]
    }
    updated = {**original, **{k: v.value for k, v in response_cookies.items()}}
    return "; ".join(f"{k}={v}" for k, v in updated.items())


@router.get("/merit_demerit", summary="解析獎懲紀錄")
async def get_merit_demerit(
    request: Request,
    response: Response,
    school_name: str,
    _cookie: str = Depends(require_cookie_header),
):
    """
    取得獎懲紀錄，回傳 JSON 格式的獎懲紀錄列表。
     - 需帶入 cookies
     - **返回值**: 包含獎懲資料的 JSON 物件。
    """
    m.SCHOOL_REQUESTS_TOTAL.labels(school_name=school_name, api_version="v8", data_type="merit_demerit").inc()

    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None
        return data

    raw_cookie_header = request.headers.get("cookie", "")
    get_cookies_url = f"{school['logined_api']}{school['cookie']['merit_demerit']}"
    merit_url = f"{school['logined_api']}{school['route']['merit_demerit']}"

    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        r = await session.get(get_cookies_url, headers={**HEADERS, "Cookie": raw_cookie_header})
        merged = merge_cookies(raw_cookie_header, r.cookies)

        merit_r = await session.get(merit_url, headers={**HEADERS, "Cookie": merged})
        original_data = await merit_r.text()

    if not original_data:
        e = send_debug_error(
            request,
            "Failed to fetch original data.",
            school_name,
            "merit_demerit",
            merit_r.status,
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = merit_r.status
        data["error_id"] = e
        data["message"] = "Failed to fetch original data."
        data["data"] = None
        return data

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = v8.parse_merit_demerit_records(original_data)

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
     - **year**: 學年篩選，民國年（如 `114`），不填則回傳全部
     - **semester**: 學期篩選，`上` 或 `下`，不填則回傳全部
     - **返回值**: 包含出勤資料的 JSON 物件。
    """
    m.SCHOOL_REQUESTS_TOTAL.labels(school_name=school_name, api_version="v8", data_type="attendance").inc()

    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None
        return data

    raw_cookie_header = request.headers.get("cookie", "")
    get_cookies_url = f"{school['logined_api']}{school['cookie']['attendance']}"
    attendance_url = f"{school['logined_api']}{school['route']['attendance']}"

    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        r = await session.get(get_cookies_url, headers={**HEADERS, "Cookie": raw_cookie_header})
        merged = merge_cookies(raw_cookie_header, r.cookies)

        attendance_r = await session.get(attendance_url, headers={**HEADERS, "Cookie": merged})
        original_data = await attendance_r.text()

    if not original_data:
        e = send_debug_error(
            request,
            "Failed to fetch original data.",
            school_name,
            "attendance",
            attendance_r.status,
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = attendance_r.status
        data["error_id"] = e
        data["message"] = "Failed to fetch original data."
        data["data"] = None
        return data

    records = v8.parse_absence_records(original_data)
    now=YearModel()
    records = [r for r in records if r["academic_year"] == now.year]

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = records

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
     - **返回值**: 包含考試選單的 JSON 物件。
    """
    m.SCHOOL_REQUESTS_TOTAL.labels(school_name=school_name, api_version="v8", data_type="exam_menu").inc()

    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None
        return data

    raw_cookie_header = request.headers.get("cookie", "")
    get_cookies_url = f"{school['logined_api']}{school['cookie']['exam_menu']}"
    exam_menu_url = f"{school['logined_api']}{school['route']['exam_menu']}"

    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        r = await session.get(get_cookies_url, headers={**HEADERS, "Cookie": raw_cookie_header})
        merged = merge_cookies(raw_cookie_header, r.cookies)

        exam_menu_r = await session.get(exam_menu_url, headers={**HEADERS, "Cookie": merged})
        original_data = await exam_menu_r.json()

    if not original_data:
        e = send_debug_error(
            request,
            "Failed to fetch original data.",
            school_name,
            "exam_menu",
            exam_menu_r.status,
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = exam_menu_r.status
        data["error_id"] = e
        data["message"] = "Failed to fetch original data."
        data["data"] = None
        return data

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = original_data

    return data


@router.get("/exam_results", summary="解析考試成績")
async def get_exam_results(
    request: Request,
    response: Response,
    school_name: str,
    exam: str,
    _cookie: str = Depends(require_cookie_header),
):
    """
    取得考試成績，回傳 JSON 格式的考試成績資料。
     - 需帶入 cookies
     - **exam**: base64 編碼的考試識別字串（從 exam_menu 取得）
     - **返回值**: 包含考試成績的 JSON 物件。
    """
    m.SCHOOL_REQUESTS_TOTAL.labels(school_name=school_name, api_version="v8", data_type="exam_results").inc()

    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None
        return data

    exam_decoded = base64.b64decode(unquote_plus(exam).replace(" ", "+")).decode()

    raw_cookie_header = request.headers.get("cookie", "")
    get_cookies_url = f"{school['logined_api']}{school['cookie']['exam_results']}"
    exam_results_url = f"{school['logined_api']}{school['route']['exam_results']}"

    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        r = await session.get(get_cookies_url, headers={**HEADERS, "Cookie": raw_cookie_header})
        merged = merge_cookies(raw_cookie_header, r.cookies)

        exam_results_r = await session.get(
            exam_results_url,
            headers={**HEADERS, "Cookie": merged},
            params={"exam": exam_decoded},
        )
        original_data = await exam_results_r.json()

    if not original_data:
        e = send_debug_error(
            request,
            "Failed to fetch original data.",
            school_name,
            "exam_results",
            exam_results_r.status,
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = exam_results_r.status
        data["error_id"] = e
        data["message"] = "Failed to fetch original data."
        data["data"] = None
        return data

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = v8.parse_exam_results(original_data)

    return data


@router.get("/semester_scores", summary="解析學期成績")
async def get_semester_scores(
    request: Request,
    response: Response,
    school_name: str,
    semester: int = 1,
    _cookie: str = Depends(require_cookie_header),
):
    """
    取得學期成績，回傳 JSON 格式的學期成績資料。
     - 需帶入 cookies
     - **semester**: 學年度（1 = 一年級、2 = 二年級、3 = 三年級），預設為 1
     - **返回值**: 包含學期成績資料的 JSON 物件。
    """
    m.SCHOOL_REQUESTS_TOTAL.labels(school_name=school_name, api_version="v8", data_type="semester_scores").inc()

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

    raw_cookie_header = request.headers.get("cookie", "")
    get_cookies_url = f"{school['logined_api']}{school['cookie']['semester_scores']}"
    semester_scores_url = f"{school['logined_api']}{school['route']['semester_scores']}"

    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        login_r = await session.get(get_cookies_url, headers={**NAV_HEADERS, "Cookie": raw_cookie_header}, allow_redirects=True)
        merged = merge_cookies(raw_cookie_header, login_r.cookies)

        check_url = str(login_r.url).rsplit("/", 1)[0] + "/CheckSchedule"
        check_r = await session.get(check_url, headers={**NAV_HEADERS, "Cookie": merged}, allow_redirects=True)
        merged = merge_cookies(merged, check_r.cookies)

        rd = {
            "option":"getTranscriptData"
        }
        semester_scores_r = await session.post(
            semester_scores_url,
            headers={**HEADERS, "Cookie": merged},
            data=rd,
        )
        original_data = await semester_scores_r.json()

    if not original_data:
        e = send_debug_error(
            request,
            "Failed to fetch original data.",
            school_name,
            "semester_scores",
            semester_scores_r.status,
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = semester_scores_r.status
        data["error_id"] = e
        data["message"] = "Failed to fetch original data."
        data["data"] = None
        return data
    r = v8.parse_semester_grades(original_data, semester)
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = r
    print(r)

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
     - **返回值**: 包含課表資料的 JSON 物件。
    """
    m.SCHOOL_REQUESTS_TOTAL.labels(school_name=school_name, api_version="v8", data_type="curriculum").inc()

    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None
        return data

    raw_cookie_header = request.headers.get("cookie", "")
    get_cookies_url = f"{school['logined_api']}{school['cookie']['curriculum']}"
    curriculum_url = f"{school['logined_api']}{school['route']['curriculum']}"

    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        login_r = await session.get(get_cookies_url, headers={**NAV_HEADERS, "Cookie": raw_cookie_header}, allow_redirects=True)
        merged = merge_cookies(raw_cookie_header, login_r.cookies)

        check_url = str(login_r.url).rsplit("/", 1)[0] + "/CheckSchedule"
        check_r = await session.get(check_url, headers={**NAV_HEADERS, "Cookie": merged}, allow_redirects=True)
        check_html = await check_r.text()
        user_info = v8.parse_inputs(check_html)

        merged = merge_cookies(merged, check_r.cookies)
        curriculum_r = await session.get(curriculum_url, headers={**HEADERS, "Cookie": merged})
        original_data = await curriculum_r.json()

    if not original_data:
        e = send_debug_error(
            request,
            "Failed to fetch original data.",
            school_name,
            "curriculum",
            curriculum_r.status,
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = curriculum_r.status
        data["error_id"] = e
        data["message"] = "Failed to fetch original data."
        data["data"] = None
        return data
    r = {}
    for i in original_data:
        if user_info['cunit_cname'] in i:
            r= v8.parse_curriculum(original_data[i])
            continue
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = r

    return data
