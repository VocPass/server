from fastapi import APIRouter, Response, Request, status, Header, Depends
from fastapi.responses import RedirectResponse
from utils.debug import Debug
from pydantic import BaseModel
from dotenv import load_dotenv

import os
import json
import aiohttp
import time
import utils.v7 as v7
from utils.base import *
from utils.http_client import HttpsClient
from utils import metrics as m
import base64
from urllib.parse import unquote_plus

load_dotenv()
router = APIRouter(prefix="/api/v7", tags=["v7 解析端點"])
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
    request: Request,
    error_message: str,
    school_name: str,
    page: str,
    status: int,
    response_body=None,
    traceback=None,
):
    client = getattr(request.app.state, "pb_client", None)
    r = Debug(client).send_error(
        error_message,
        school_name,
        page,
        status,
        response_body=response_body,
        traceback=traceback,
    )
    return r


headers = {
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


async def goto_page(cookies, root, endpoint: list, years: list,only_two=False):

    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(
        cookies=cookies, headers=headers, cookie_jar=jar
    ) as session:
        async with session.get(f"{root}Main.aspx", ssl=False) as resp:
            text = await resp.text()
        for menu in endpoint:
            href = v7.parse_href(text)[menu]
            async with session.post(
                v7.urljoin(root, href), data=v7.parse_inputs(text)
            ) as resp:
                text = await resp.text()

        link = v7.parse_iframes(text)["iframecontent"]
        iframe_url = v7.urljoin(root, link)
        async with session.get(iframe_url) as resp:
            text = await resp.text()
        last_action = text

        all_data = []
        data = v7.parse_inputs(text)
        print( v7.parse_links(text))
        if only_two:
            if len(years)%2 != 0:
                # 上學期
                years = years[:-1]
            else:
                # 下學期
                years = years[-2:]
            print(years)
            
        for year in years:
            if year not in v7.parse_links(text):
                continue
            data["__EVENTTARGET"] = v7.parse_links(text)[year]
            async with session.post(iframe_url, data=data) as resp:
                text = await resp.text()
                all_data.append(text)

    return all_data or last_action


async def goto_scores(
    cookies, root, endpoint: list, years: list, exam_no: str, return_menu=False
):

    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(
        cookies=cookies, headers=headers, cookie_jar=jar
    ) as session:
        async with session.get(f"{root}Main.aspx", ssl=False) as resp:
            text = await resp.text()
        for menu in endpoint:
            href = v7.parse_href(text)[menu]
            async with session.post(
                v7.urljoin(root, href), data=v7.parse_inputs(text)
            ) as resp:
                text = await resp.text()

        link = v7.parse_iframes(text)["iframecontent"]
        iframe_url = v7.urljoin(root, link)
        async with session.get(iframe_url) as resp:
            text = await resp.text()
        last_action = text

        all_data = []
        data = v7.parse_inputs(text)
        uid = v7.parse_select(text, "DdlStd_yearterm_ddl")
        no_uid = v7.parse_select(text, "DdlStd_exam_no_ddl")

        if return_menu:
            return no_uid, uid
        for year in years:
            if uid.get(year) is None:
                continue
            data["__EVENTTARGET"] = "DdlStd_yearterm_ddl"
            data["DdlStd_exam_no_ddl"] = exam_no
            data["DdlStd_yearterm_ddl"] = uid[year]
            async with session.post(iframe_url, data=data) as resp:
                text = await resp.text()
                all_data.append(text)

    return all_data or last_action


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

    m.SCHOOL_REQUESTS_TOTAL.labels(
        school_name=school_name, api_version="v7", data_type="merit_demerit"
    ).inc()
    url = f"{school['api']}{school['url']['root']}"

    original_data = await goto_page(
        request.cookies,
        url,
        school["endpoint_action"]["merit_demerit"],
        ["一上", "一下", "二上", "二下", "三上", "三下"],
    )

    r = v7.parse_merit_demerit_records(original_data)

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

    m.SCHOOL_REQUESTS_TOTAL.labels(
        school_name=school_name, api_version="v7", data_type="attendance"
    ).inc()
    url = f"{school['api']}{school['url']['root']}"

    original_data = await goto_page(
        request.cookies, url, school["endpoint_action"]["attendance"], ["一上","一下","二上","二下","三上","三下"],True
    )
    r = []
    for i in original_data:
        r.extend(v7.parse_absence_records(i))

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

    m.SCHOOL_REQUESTS_TOTAL.labels(
        school_name=school_name, api_version="v7", data_type="exam_menu"
    ).inc()
    url = f"{school['api']}{school['url']['root']}"

    original_data = await goto_scores(
        request.cookies, url, school["endpoint_action"]["exam_menu"], [], "", True
    )
    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    exam_types, semesters = original_data
    
    data["data"] = [
        {"name": f"[{sem}] {exam}", "url":sem+","+exam}
        for sem, sem_val in semesters.items()
        for exam, exam_val in exam_types.items()
    ]
    return data


@router.get("/exam_results", summary="解析考試成績")
async def get_exam_results(
    request: Request, exam: str, response: Response,school_name: str, _cookie: str = Depends(require_cookie_header)
):
    """
    取得考試成績，回傳 JSON 格式的考試成績資料。
     - 需帶入 cookies
     - **返回值**: 包含學期成績資料的 JS
    """
    school = request.app.state.schools.get(school_name)
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data = request.app.state.response
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None

        return data
    
    exam = base64.b64decode(unquote_plus(exam).replace(" ","+")).decode()
    sem_val, exam_val = exam.split(",")

    url = f"{school['api']}{school['url']['root']}"
    original_data = await goto_scores(
        request.cookies, url, school["endpoint_action"]["exam_results"], [sem_val], exam_val
    )
    
    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = v7.parse_exam_results(original_data[0])

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
    semester_str = ["一上", "二上", "三上"][semester - 1]

    school_info = request.app.state.schools.get(school_name)
    if not school_info:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None

        return data

    m.SCHOOL_REQUESTS_TOTAL.labels(
        school_name=school_name, api_version="v7", data_type="semester_scores"
    )
    url = f"{school_info['api']}{school_info['url']['root']}"
    original_data = await goto_scores(
        request.cookies,
        url,
        school_info["endpoint_action"]["semester_scores"],
        [semester_str],
        "學年",
    )
    r = v7.parse_semester_grades(original_data[0])

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = r

    return data


@router.get("/curriculum", summary="解析課表")
async def get_curriculum(
    request: Request,
    response: Response,
    school_name: str,
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
    url = f"{school['api']}{school['url']['root']}"

    m.SCHOOL_REQUESTS_TOTAL.labels(
        school_name=school_name, api_version="v7", data_type="curriculum"
    )
    original_data = await goto_page(
        request.cookies,
        url,
        school["endpoint_action"]["curriculum"],
        ["Tabswitch1_rbl_1"],
    )
    r = v7.parse_curriculum(original_data)

    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = r

    return data
