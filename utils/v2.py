from utils.base import *
import re
from bs4 import BeautifulSoup


def _score_to_number(value):
    if value is None:
        return None

    text = str(value).strip()
    if not text or text == "-":
        return None

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _build_course_key(course):
    return (
        course.get("CourseID")
        or course.get("OCID")
        or course.get("OpTitle")
        or ""
    )


def _build_semester_payload(course):
    if not course:
        return {
            "type": "",
            "credits": "",
            "score": "-",
        }

    return {
        "type": course.get("StudyType", ""),
        "credits": str(course.get("Credit", "")),
        "score": course.get("AllScore", "-"),
    }


def get_request_verification_token(html_content):
    """
    取得頁面中的 __RequestVerificationToken。
    """
    soup = BeautifulSoup(html_content, "html.parser")
    token_input = soup.find("input", {"name": "__RequestVerificationToken"})
    if not token_input:
        return None

    return token_input.get("value")


def parse_curriculum(curriculum_data,school_info):
    """
    解析課表
    """
    data = {}
    time = {}

    if curriculum_data['TimeList'] == []:
        time = school_info['time']
    else:
        for i in curriculum_data["TimeList"]:
            time[i["Paike"]] = {
                "start": i["BegTime"],
                "end": i["EndTime"],
            }

    for i in curriculum_data["MyCosTableS"]:

        if data.get(i["CosTitle"]):
            data[i["CosTitle"]]["count"] += 1
        else:
            data[i["CosTitle"]] = {"schedule": [], "count": 1}
        data[i["CosTitle"]]["schedule"].append(
            {
                "weekday": num_to_chinese(i["DayOfWeek"]),
                "period": num_to_chinese(i["PaiKe"]),
                "start": time[str(i["PaiKe"])]["start"],
                "end": time[str(i["PaiKe"])]["end"],
            }
        )
    return data


def parse_merit_demerit_records(records):
    """
    解析獎懲紀錄
    """
    good = ["大功", "小功", "嘉獎"]
    bad = ["大過", "小過", "警告"]

    data = [[], []]
    for record in records["obj"]["ListD"]:
        i = 3
        if record["RewardItem"][:2] in good:
            i = 0
        elif record["RewardItem"][:2] in bad:
            i = 1
        date = YearModel(record["RdDate"].replace("-", "/"))
        data[i].append(
            {
                "date_occurred": record["RdDate"].replace("-", "/"),
                "date_approved": (
                    record["RdDate"].replace("-", "/")
                    if record["ReformStatusText"] != "申請中"
                    else "申請中"
                ),
                "reason": record["Descript"],
                "action": record["RewardItem"],
                "date_revoked": None,  # 佔位
                "year": f"{date.year}{date.semester}",
            }
        )

    return data


def parse_semester_grades(first_semester_grades, second_semester_grades):
    data = {
        "student_info": first_semester_grades["obj"]["StuName"],
        "subject_scores": [],
    }

    first_courses = first_semester_grades["obj"].get("DataList", [])
    second_courses = second_semester_grades["obj"].get("DataList", [])

    second_courses_by_key = {}
    for course in second_courses:
        key = _build_course_key(course)
        if key not in second_courses_by_key:
            second_courses_by_key[key] = []
        second_courses_by_key[key].append(course)

    matched_second_course_ids = set()

    for first in first_courses:
        key = _build_course_key(first)
        candidates = second_courses_by_key.get(key, [])
        second = candidates.pop(0) if candidates else None

        if second is None:
            for candidate in second_courses:
                if candidate.get("Objid") in matched_second_course_ids:
                    continue
                if candidate.get("OpTitle") == first.get("OpTitle"):
                    second = candidate
                    break

        if second is not None and second.get("Objid"):
            matched_second_course_ids.add(second.get("Objid"))

        first_score = _score_to_number(first.get("AllScore"))
        second_score = _score_to_number(second.get("AllScore") if second else None)

        annual_score = None
        if first_score is not None and second_score is not None:
            annual_score = int((first_score + second_score) // 2)
        elif first_score is not None:
            annual_score = int(first_score)
        elif second_score is not None:
            annual_score = int(second_score)

        d = {
            "subject": first.get("OpTitle", ""),
            "first_semester": _build_semester_payload(first),
            "second_semester": _build_semester_payload(second),
            "annual_score": annual_score,
        }
        data["subject_scores"].append(d)

    for second in second_courses:
        if second.get("Objid") in matched_second_course_ids:
            continue

        second_score = _score_to_number(second.get("AllScore"))

        d = {
            "subject": second.get("OpTitle", ""),
            "first_semester": _build_semester_payload(None),
            "second_semester": _build_semester_payload(second),
            "annual_score": int(second_score) if second_score is not None else None,
        }
        data["subject_scores"].append(d)

    return data


def parse_absence_records(html_content):
    def normalize_period(text):
        full_to_half = str.maketrans("０１２３４５６７８９", "0123456789")
        normalized = text.translate(full_to_half)
        match = re.search(r"(\d+)", normalized)
        return match.group(1) if match else ""

    def map_cell_status(text):
        value = text.strip()
        status_map = {
            "缺席": "曠",
            "曠課": "曠",
            "遲到": "遲",
            "公假": "公",
            "公勤": "公",
            "事假": "事",
            "病假": "病",
            "喪假": "喪",
            "生理假": "生",
            "生理": "生",
        }
        if not value:
            return ""
        if value in status_map:
            return status_map[value]
        return value[0]

    def get_academic_term(date_text):
        match = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", date_text)
        if not match:
            return ""
        month = int(match.group(2))
        return "上" if month >= 8 or month <= 1 else "下"

    soup = BeautifulSoup(html_content, "html.parser")
    table = soup.find("table", id="MyList")
    if not table:
        return []

    header_cells = table.select("thead tr th")
    periods = [normalize_period(cell.get_text(strip=True)) for cell in header_cells[2:]]

    result = []
    for row in table.select("tbody tr.MyRow"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        date = cells[0].get_text(strip=True)
        weekday = cells[1].get_text(strip=True)
        academic_term = get_academic_term(date)

        for index, period_cell in enumerate(cells[2:]):
            if index >= len(periods):
                continue

            mapped_cell = map_cell_status(period_cell.get_text(strip=True))
            if not mapped_cell:
                continue

            result.append(
                {
                    "academic_term": academic_term,
                    "date": date,
                    "weekday": weekday,
                    "period": periods[index],
                    "cell": mapped_cell,
                }
            )

    return result

def parse_grade_level(info):
    text = info.get("obj", {}).get("OrgTitle")
    if not text:
        return 1
    else:
        text = text[-2]
    y = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
    }
    return y[text] if text in "一二三四" else 1