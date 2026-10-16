"""新北市 ESA 登入、HSA 高中職資料查詢端點。"""

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from utils import metrics as m
from utils import v10
from utils.esa_client import EsaError, open_esa_client

router = APIRouter(prefix="/api/v10", tags=["v10 新北高中職解析端點"])


def require_cookie_header(cookie: str = Header(..., alias="Cookie", description="ESA 登入後的 Cookie 標頭")):
    return cookie


def get_school(request, school_name):
    school = request.app.state.schools.get(school_name)
    if not school or school.get("vision") != "v10":
        raise EsaError(400, "Unsupported school.")
    return school


async def run_query(request, response, school_name, endpoint, operation):
    m.SCHOOL_REQUESTS_TOTAL.labels(school_name=school_name, api_version="v10", data_type=endpoint).inc()
    try:
        school = get_school(request, school_name)
        async with open_esa_client(request.cookies, school, school_name) as client:
            result = await operation(client)
        return {"code": 200, "message": "Success.", "data": result}
    except EsaError as exc:
        response.status_code = exc.code
        return {"code": exc.code, "message": str(exc), "data": None}
    except ValueError:
        response.status_code = 502
        return {"code": 502, "message": "Unexpected school response format.", "data": None}


async def score_page(client):
    await client.open_system("scores")
    return await client.get(client.school["route"]["semester_scores"], "score_options")


async def term_scores(client, year, term):
    return await client.post(client.school["route"]["semester_scores"], "scores",
                             {"sbj_year": str(year), "sbj_sem": str(term)})


@router.get("/merit_demerit", summary="解析獎懲紀錄")
async def get_merit_demerit(request: Request, response: Response, school_name: str,
                          _cookie: str = Depends(require_cookie_header)):
    async def operation(client):
        await client.open_system("affairs")
        await client.get(client.school["route"]["merit_page"], "merit_page")
        html = await client.get(client.school["route"]["merit_demerit"], "merit_demerit")
        return v10.parse_merit_demerit_records(html)
    return await run_query(request, response, school_name, "merit_demerit", operation)


@router.get("/attendance", summary="解析歷年出缺席紀錄")
async def get_attendance(request: Request, response: Response, school_name: str,
                         _cookie: str = Depends(require_cookie_header)):
    async def operation(client):
        await client.open_system("affairs")
        html = await client.get(client.school["route"]["attendance"], "attendance")
        return v10.parse_absence_records(html)
    return await run_query(request, response, school_name, "attendance", operation)


@router.get("/exam_menu", summary="解析已公布的考試選單")
async def get_exam_menu(request: Request, response: Response, school_name: str,
                        _cookie: str = Depends(require_cookie_header)):
    async def operation(client):
        page = await score_page(client)
        years = v10.parse_options(page, "#sbj_year")
        terms = v10.parse_options(page, "#sbj_sem")
        if not years or not terms:
            raise ValueError("Missing score options.")
        tables = []
        # A single school session is used sequentially: these pages keep query state.
        for year in years:
            for term in terms:
                tables.append((year, term, await term_scores(client, year, term)))
        return v10.parse_exam_menu(tables)
    return await run_query(request, response, school_name, "exam_menu", operation)


@router.get("/exam_results", summary="解析考試成績")
async def get_exam_results(request: Request, response: Response, school_name: str,
                           exam: str = Query(..., pattern=r"^\d{3}:([12]):([1234])$",
                                             description="exam_menu 回傳的 url 值，例如 114:1:1"),
                           _cookie: str = Depends(require_cookie_header)):
    async def operation(client):
        page = await score_page(client)
        year, term, key = exam.split(":")
        if year not in v10.parse_options(page, "#sbj_year") or term not in v10.parse_options(page, "#sbj_sem"):
            raise EsaError(400, "Invalid exam selection.")
        html = await term_scores(client, year, term)
        result = v10.parse_exam_results(html, exam, client.student_name)
        if not result["subjects"]:
            raise EsaError(404, "Exam results are not published or unavailable.")
        return result
    return await run_query(request, response, school_name, "exam_results", operation)


@router.get("/semester_scores", summary="解析一個年級的上下學期成績")
async def get_semester_scores(request: Request, response: Response, school_name: str,
                              semester: int = Query(1, ge=1, le=3, description="年級：1、2、3"),
                              _cookie: str = Depends(require_cookie_header)):
    async def operation(client):
        page = await score_page(client)
        years = v10.parse_options(page, "#sbj_year")
        if not years:
            raise ValueError("Missing school years.")
        year = min(map(int, years)) + semester - 1
        if str(year) not in years:
            raise EsaError(404, "No records for this grade.")
        first = await term_scores(client, year, 1)
        second = await term_scores(client, year, 2)
        result = v10.parse_semester_grades(first, second, client.student_name)
        if not result["subject_scores"]:
            raise EsaError(404, "Semester scores are not published or unavailable.")
        return result
    return await run_query(request, response, school_name, "semester_scores", operation)


@router.get("/curriculum", summary="課表（目前資料來源未提供可用課表）")
async def get_curriculum(request: Request, response: Response, school_name: str,
                          _cookie: str = Depends(require_cookie_header)):
    m.SCHOOL_REQUESTS_TOTAL.labels(school_name=school_name, api_version="v10", data_type="curriculum").inc()
    try:
        get_school(request, school_name)
    except EsaError as exc:
        response.status_code = exc.code
        return {"code": exc.code, "message": str(exc), "data": None}
    response.status_code = 404
    return {"code": 404, "message": "Curriculum is not available from this school system.", "data": None}
