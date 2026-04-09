import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def parse_inputs(html):
    """解析所有 <input> 標籤，回傳 {"name/id": "value"}"""
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    for inp in soup.find_all("input"):
        key = inp.get("name") or inp.get("id")
        if key:
            result[key] = inp.get("value", "")
    return result


def parse_merit_demerit_records(html):
    """
    解析獎懲紀錄，回傳 [merits, demerits] 各為 list of dict
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="gridtable")
    if not table:
        return [[], []]

    merit_keywords = {"嘉獎", "小功", "大功"}
    demerit_keywords = {"警告", "小過", "大過"}

    merits, demerits = [], []

    for row in table.find("tbody").find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        # 學年學期：e.g. "113 上學期"
        year_text = cells[0].get_text(separator=" ", strip=True)
        year_match = re.search(r"(\d+)", year_text)
        if not year_match:
            continue
        roc_year = int(year_match.group(1))
        semester = "1" if "上" in year_text else "2"
        year_code = f"{roc_year}{semester}"

        # 日期：ROC "113-11-11" → Gregorian "2024/11/11"
        date_roc = cells[1].get_text(strip=True)
        parts = date_roc.split("-")
        date_gregorian = f"{int(parts[0]) + 1911}/{parts[1]}/{parts[2]}" if len(parts) == 3 else date_roc

        # 獎懲內容：移除「項目：」前綴
        span = cells[2].find("span")
        action = (span.get_text(strip=True) if span else cells[2].get_text(strip=True))
        action = re.sub(r"^項目：", "", action).strip()

        # 獎懲事由
        reason = cells[3].get_text(strip=True)

        record = {
            "date_occurred": date_gregorian,
            "date_approved": date_gregorian,
            "reason": reason,
            "action": action,
            "date_revoked": None,
            "year": year_code,
        }

        if any(kw in action for kw in merit_keywords):
            merits.append(record)
        elif any(kw in action for kw in demerit_keywords):
            demerits.append(record)

    return [merits, demerits]



def parse_absence_records(absence):
    """
    解析出勤紀錄，回傳 list of dict
    每筆 dict: {academic_term, date, weekday, period, cell}
    """
    PERIOD_LABELS = ["升旗", "早自習", "1", "2", "3", "4", "午休", "5", "6", "7", "8", "9"]
    CELL_MAP = {
        "曠課": "曠", "遲到": "遲", "病假": "病", "事假": "事",
        "公假": "公", "喪假": "喪", "其他特殊事故": "其他",
        "產前假": "產前", "娩假": "娩", "流產假": "流產",
        "育嬰假": "育嬰", "生理假": "生理", "婚假": "婚",
        "陪產假": "陪產", "身心調適假": "身心",
    }

    soup = BeautifulSoup(absence, "html.parser")
    tables = soup.find_all("table")
    detail_table = tables[-1]

    records = []
    for row in detail_table.find_all("tr")[1:]:  # 跳過表頭
        cells = row.find_all("td")
        if len(cells) < 17:
            continue

        term_text = cells[0].get_text(strip=True)   # e.g. "114/下"
        academic_term = term_text.split("/")[-1]    # "上" or "下"

        date_roc = cells[3].get_text(strip=True)    # e.g. "115/03/25"
        parts = date_roc.split("/")
        date_gregorian = f"{int(parts[0]) + 1911}/{int(parts[1])}/{int(parts[2])}"

        weekday = cells[4].get_text(strip=True)

        for i, label in enumerate(PERIOD_LABELS):
            cell_val = cells[5 + i].get_text(strip=True)
            if cell_val:
                records.append({
                    "academic_term": academic_term,
                    "date": date_gregorian,
                    "weekday": weekday,
                    "period": label,
                    "cell": CELL_MAP.get(cell_val, cell_val),
                })

    return records

def parse_curriculum(raw):
    """
    解析課表
    將 response.json 格式轉換成 curriculum.json 格式
    """
    WEEKDAY_MAP = {"1": "一", "2": "二", "3": "三", "4": "四", "5": "五"}
    PERIOD_MAP = {"1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六", "7": "七", "8": "八", "9": "九", "10": "十", "11": "十一", "12": "十二"}
    TIME_MAP = {
        "1": ("08:10", "09:00"),
        "2": ("09:10", "10:00"),
        "3": ("10:10", "11:00"),
        "4": ("11:10", "12:00"),
        "5": ("13:10", "14:00"),
        "6": ("14:10", "15:00"),
        "7": ("15:10", "16:00"),
        "8": ("16:10", "17:00"),
        "9": ("17:10", "18:00"),
        "10": ("18:10", "19:00"),
        "11": ("19:10", "20:00"),
        "12": ("20:10", "21:00"),
    }

    result = {}
    for entry in raw:
        name = entry["curr_cname"]
        sday = str(entry["sday"])
        speriod = str(entry["speriod"])

        slot = {
            "weekday": WEEKDAY_MAP[sday],
            "period": PERIOD_MAP[speriod],
            "start": TIME_MAP[speriod][0],
            "end": TIME_MAP[speriod][1],
        }

        if name not in result:
            result[name] = {"count": 0, "schedule": []}

        if slot not in result[name]["schedule"]:
            result[name]["schedule"].append(slot)
            result[name]["count"] += 1

    return result

def parse_semester_grades(semester_grades):
    """
    解析學期成績
    將 gradeOneJson / gradeTwoJson / gradeThreeJson 格式轉換成 semester_scores 格式
    """
    COURSE_TYPE_MAP = {"部": "必修", "校": "必修", "選": "選修"}

    def parse_earned(credits_str):
        """'28/32' → '28'，'/' → ''"""
        if not credits_str:
            return ""
        parts = credits_str.split("/")
        return parts[0] if parts[0] else ""

    subject_scores = []
    for subj in semester_grades.get("subjects", []):
        if not subj.get("currCname"):
            continue
        course_type = COURSE_TYPE_MAP.get(subj.get("courseType", ""), subj.get("courseType", ""))
        subject_scores.append({
            "subject": subj["currCname"],
            "first_semester": {
                "type": course_type,
                "credits": subj.get("sem1_credits", ""),
                "score": subj.get("sem1_score", ""),
            },
            "second_semester": {
                "type": course_type,
                "credits": subj.get("sem2_credits", ""),
                "score": subj.get("sem2_score", ""),
            },
            "annual_score": subj.get("year_score", ""),
        })

    total_scores = {
        "學科平均": {
            "first_semester": semester_grades.get("sem1ScoreAvg", ""),
            "second_semester": semester_grades.get("sem2ScoreAvg", ""),
            "annual": semester_grades.get("yearScoreAvg", ""),
        },
        "實得學分": {
            "first_semester": parse_earned(semester_grades.get("sem1ActualTotalCredits", "/")),
            "second_semester": parse_earned(semester_grades.get("sem2ActualTotalCredits", "/")),
            "annual": "",
        },
        "實得累計": {
            "first_semester": parse_earned(semester_grades.get("accumulateCredits", "")),
            "second_semester": "",
            "annual": "",
        },
        "學期名次": {
            "first_semester": semester_grades.get("sem1ClassRank", ""),
            "second_semester": semester_grades.get("sem2ClassRank", ""),
            "annual": "",
        },
    }

    return {
        "subject_scores": subject_scores,
        "total_scores": total_scores,
        "daily_performance": {
            "first_semester": {},
            "second_semester": {},
        },
    }

def parse_exam_results(exam):
    """
    解析考試成績
    """
