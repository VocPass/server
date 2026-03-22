from fastapi import APIRouter, Response, Request, status, Header, Depends
from pydantic import BaseModel
from dotenv import load_dotenv

import json
import urllib.parse

import utils.v6 as v6
from utils.http import HttpsClient

load_dotenv()
router = APIRouter(prefix="/api/v6", tags=["v6 解析端點"])
http = HttpsClient()


class HTMLInput(BaseModel):
    html: str


def require_cookie_header(
    cookie: str = Header(
        ...,
        alias="Cookie",
        description="登入後取得的 Cookie 標頭（需含 user_session）",
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
    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None
        return data

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = [[], []]
    return data


@router.get("/curriculum", summary="解析課表")
async def get_curriculum(
    request: Request,
    response: Response,
    school_name: str,
    _cookie: str = Depends(require_cookie_header),
):
    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None
        return data

    user_session = request.cookies.get("user_session")
    if not user_session:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Missing user_session cookie."
        data["data"] = None
        return data

    path = school["route"]["curriculum"].replace(
        "{user_session}", urllib.parse.quote(user_session, safe="")
    )
    url = f"{school['api']}{path}"
    original_data = await http.get(url, request.cookies, "utf-8")

    if original_data.code != 200:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = original_data.code
        data["message"] = "Failed to fetch original data."
        data["data"] = None
        return data

    payload = original_data.data
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            data["code"] = 500
            data["message"] = "Failed to parse response."
            data["data"] = None
            return data

    parsed, err = v6.parse_curriculum(payload)
    if err:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        data["code"] = 401
        data["message"] = err
        data["data"] = None
        return data

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = parsed
    return data


@router.get("/attendance", summary="解析出缺紀錄")
async def get_attendance(
    request: Request,
    response: Response,
    school_name: str,
    _cookie: str = Depends(require_cookie_header),
):
    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None
        return data

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = []
    return data


@router.get("/exam_menu", summary="解析考試選單")
async def get_exam_menu(
    request: Request,
    response: Response,
    school_name: str,
    _cookie: str = Depends(require_cookie_header),
):
    school = request.app.state.schools.get(school_name)
    data = request.app.state.response
    if not school:
        response.status_code = status.HTTP_400_BAD_REQUEST
        data["code"] = 400
        data["message"] = "Unsupported school."
        data["data"] = None
        return data

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = []
    return data


@router.post("/exam_results", summary="解析考試成績")
async def get_exam_results(
    item: HTMLInput, request: Request, exam: str, response: Response
):
    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = {}
    return data


@router.get("/semester_scores", summary="解析學期成績")
async def get_semester_scores(
    response: Response,
    request: Request,
    school_name: str,
    semester: int = 1,
    _cookie: str = Depends(require_cookie_header),
):
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

    data["code"] = 200
    data["message"] = "Success."
    data["data"] = {
        "student_info": "",
        "subject_scores": [],
        "total_scores": {},
        "daily_performance": {},
    }
    return data
