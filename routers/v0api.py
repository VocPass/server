from fastapi import APIRouter, Response, Request
from fastapi.responses import RedirectResponse
from utils.debug import Debug
from pydantic import BaseModel
from dotenv import load_dotenv

import os
import json
import aiohttp
import utils.v1 as v1


load_dotenv()
router = APIRouter(prefix="/api/v0", tags=["v0 解析端點"])

class HTMLInput(BaseModel):
    html: str

def send_debug_error(request: Request, error_message: str, school_name: str, page: str):
    client = getattr(request.app.state, "pb_client", None)
    Debug(client).send_error(error_message, school_name, page)

@router.post("/merit_demerit", summary="解析獎懲紀錄")
async def get_merit_demerit(request: Request, item: HTMLInput):
    """
    解析獎懲紀錄的 HTML，回傳 JSON 格式的獎懲紀錄列表。
     - **html**: 課程表的 HTML 字串。
     - **返回值**: 包含獎懲紀錄列表的 JSON 物件。
    """
    r = v1.parse_merit_demerit_records(item.html)

    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = r

    return data


@router.post("/curriculum", summary="解析課表")
async def get_curriculum(request: Request, item: HTMLInput):
    """
    解析課表的 HTML，回傳 JSON 格式的課程表資料。
     - **html**: 課程表的 HTML 字串。
     - **返回值**: 包含課程表資料的 JSON 物件。
    
    """
    r = v1.parse_weekly_curriculum(item.html)
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


@router.post("/attendance", summary="解析出缺紀錄")
async def get_attendance(item: HTMLInput, request: Request):
    """
    解析出勤紀錄的 HTML，回傳 JSON 格式的出勤紀錄列表。
     - **html**: 出勤紀錄的 HTML 字串。
     - **返回值**: 包含出勤紀錄列表的 JSON 物件。
    """
    r = v1.parse_absence_records(item.html, filter_types=[])
    
    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = r

    return data


@router.post("/exam_menu", summary="解析考試選單")
async def get_exam_menu(item: HTMLInput, request: Request):
    """
    解析考試選單的 HTML，回傳 JSON 格式的考試選單資料。
     - **html**: 考試選單的 HTML 字串。
     - **返回值**: 包含考試選單資料的 JSON 物件。
     - **考試選單資料格式**: 包含以下欄位：
    """
    r = v1.parse_exam_menu(item.html)

    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = r

    return data

@router.post("/exam_results", summary="解析考試成績")
async def get_exam_results(item: HTMLInput, request: Request):
    """
    解析考試成績的 HTML，回傳 JSON 格式的考試成績資料。
     - **html**: 考試成績的 HTML 字串。
     - **返回值**: 包含考試成績資料的 JSON 物件。
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

@router.post("/semester_scores", summary="解析學期成績")
async def get_semester_scores(item: HTMLInput, request: Request):
    """
    解析學期成績的 HTML，回傳 JSON 格式的學期成績資料。
     - **html**: 學期成績的 HTML 字串。
     - **返回值**: 包含學期成績資料的 JSON 物件。
    """
    
    r = v1.StudentGradeExtractor(item.html)
    r = r.get_all_grade_data()
    
    
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