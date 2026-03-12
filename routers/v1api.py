from fastapi import APIRouter, Response, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import os
import json
import aiohttp
import utils.v1 as v1

load_dotenv()
router = APIRouter(prefix="/api/v1", tags=["v1 解析端點"])


class HTMLInput(BaseModel):
    html: str


@router.get("/", summary="獲取v1支援學校列表")
async def index(request: Request):
    """
    獲取 v1 樣式解析支援的學校列表。
     - **返回值**: 包含支援學校列表的 JSON 物件。
     - **範例**:
        ```json
        ["臺北市立大學附屬高級中學", "臺北市立大學附屬實驗國民小學"]
        ```
    """
    data = request.app.state.response
    async with aiohttp.ClientSession() as session:
        async with session.get(os.getenv("SCHOOL_URL")) as resp:
            if resp.status == 200:
                schools = json.loads(await resp.text())

            else:
                data["code"] = 500
                data["message"] = "Failed to fetch school list."

                return data

    data["code"] = 200
    data["message"] = "Success."
    supported_schools = []
    for i in schools:
        if schools[i].get("vision") == "v1":
            supported_schools.append(i)
    data["data"] = supported_schools

    return data


@router.get("/merit_demerit", summary="解析獎懲紀錄")
async def get_merit_demerit(request: Request, item: HTMLInput):
    """
    解析獎懲紀錄的 HTML，回傳 JSON 格式的獎懲紀錄列表。
     - **html**: 獎懲紀錄的 HTML 字串。
     - **返回值**: 包含獎懲紀錄列表的 JSON 物件。
     - **獎懲紀錄格式**: 每筆紀錄包含以下欄位：
       - **type**: 獎懲類型（"merit" 或 "demerit"）。
       - **date**: 獎懲日期，格式為 "YYYY-MM-DD"。
       - **reason**: 獎懲事由。
       - **points**: 獎懲點數，正數表示獎勵，負數表示懲戒。
     - **範例**:
        ```json
        [
            {
            "date_occurred": "2023/12/29",
            "date_approved": "2024/01/02",
            "reason": "擔任班長認真負責",
            "action": "嘉獎貳次",
            "date_revoked": null,
            "year": "1121"
            }
        ]
       ```
    """
    r = v1.parse_merit_demerit_records(item.html)
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


@router.get("/curriculum", summary="解析課表")
async def get_curriculum(request: Request, item: HTMLInput):
    """
    解析課表的 HTML，回傳 JSON 格式的課程表資料。
     - **html**: 課程表的 HTML 字串。
     - **返回值**: 包含課程表資料的 JSON 物件。
     - **課程表資料格式**: 包含以下欄位：
       - **weekday**: 星期幾。
       - **count**: 每週課程節次。
       - **period**: 節次。
     - **範例**:
        ```json
        {
            "英語文": {
                "count": 2,
                "schedule": [
                {
                    "weekday": "一",
                    "period": "一"
                },
                {
                    "weekday": "一",
                    "period": "二"
                }
                ]
            }
        }
       ```
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


@router.get("/attendance", summary="解析出缺紀錄")
async def get_attendance(item: HTMLInput, request: Request):
    """
    解析出勤紀錄的 HTML，回傳 JSON 格式的出勤紀錄列表。
     - **html**: 出勤紀錄的 HTML 字串。
     - **返回值**: 包含出勤紀錄列表的 JSON 物件。
     - **出勤紀錄格式**: 每筆紀錄包含以下欄位：
         - **date**: 出勤日期，格式為 "YYYY-MM-DD"。
         - **status**: 出勤狀態（"present"、"absent"、"late"、"early_leave"）。
         - **reason**: 缺曠事由（如果有的話）。
     - **範例**:
        ```json
        [
            {
                "學年": "上",
                "日期": "2025/9/9",
                "星期": "二",
                "節次": "1",
                "狀態": "遲"
            }
        ]
        ```
    """
    r = v1.parse_absence_records(item.html, filter_types=[])
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


@router.get("/exam_menu", summary="解析考試選單")
async def get_exam_menu(item: HTMLInput, request: Request):
    """
    解析考試選單的 HTML，回傳 JSON 格式的考試選單資料。
     - **html**: 考試選單的 HTML 字串。
     - **返回值**: 包含考試選單資料的 JSON 物件。
     - **考試選單資料格式**: 包含以下欄位：
    """
    r = v1.parse_exam_menu(item.html)
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
