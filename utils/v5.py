from utils.base import *
import re
from bs4 import BeautifulSoup


def parse_merit_demerit_records(records):
    """
    解析獎懲紀錄
    """
    num_map = {"1": "乙", "2": "貳", "3": "參", "4": "肆", "5": "伍", "6": "陸", "7": "柒", "8": "捌", "9": "玖"}

    merit_fields = [(1, "嘉獎"), (2, "小功"), (3, "大功")]
    demerit_fields = [(4, "警告"), (5, "小過"), (6, "大過")]

    def tw_date_to_str(tw_date):
        if not tw_date:
            return None
        parts = tw_date.split("/")
        if len(parts) != 3:
            return tw_date
        try:
            y = int(parts[0]) + 1911
            return f"{y}/{int(parts[1]):02d}/{int(parts[2]):02d}"
        except Exception:
            return tw_date

    def build_action(row, fields):
        parts = []
        for idx, name in fields:
            cnt = row.get(f"vo.reward{idx}", 0) or 0
            if cnt > 0:
                parts.append(f"{name}{num_map.get(str(cnt), str(cnt))}次")
        return " ".join(parts)

    merits = []
    demerits = []

    for row in records.get("dataRows", []):
        merit_action = build_action(row, merit_fields)
        demerit_action = build_action(row, demerit_fields)

        syear = row.get("vo.syear", "")
        seme = row.get("vo.seme", "")
        year = f"{syear}{seme}" if syear and seme else ""

        cancel_dt = tw_date_to_str(row.get("vo.cancelDt"))

        if merit_action:
            merits.append({
                "date_occurred": tw_date_to_str(row.get("vo.happenDt")),
                "date_approved": tw_date_to_str(row.get("vo.examineDt")),
                "reason": row.get("vo.fact", ""),
                "action": merit_action,
                "date_revoked": cancel_dt,
                "year": str(year),
            })

        if demerit_action:
            demerits.append({
                "date_occurred": tw_date_to_str(row.get("vo.happenDt")),
                "date_approved": tw_date_to_str(row.get("vo.examineDt")),
                "reason": row.get("vo.fact", ""),
                "action": demerit_action,
                "date_revoked": cancel_dt,
                "year": str(year),
            })

    return [merits, demerits]



def parse_absence_records(absence):
    """
    解析出勤紀錄
    """
    import datetime

    absence_code_map = {
        "1": "曠",
        "2": "事",
        "3": "病",
        "4": "喪",
        "5": "公",
        "6": "生",
        "7": "遲",
    }
    # lesson1 → 朝會, lesson2 → period "1", lesson3 → "2", ..., lesson9 → "8"
    # morn → "早", rest → "午"
    lesson_period_map = {1: "朝", 2: "1", 3: "2", 4: "3", 5: "4", 6: "5", 7: "6", 8: "7", 9: "8"}
    weekday_map = {0: "一", 1: "二", 2: "三", 3: "四", 4: "五", 5: "六", 6: "日"}
    seme_map = {1: "上", 2: "下"}

    records = []
    rows = absence.get("dataRows", [])

    # detect whether keys use "vo." prefix
    prefix = ""
    if rows and "vo.absenceDt" in rows[0]:
        prefix = "vo."

    for row in rows:
        date_tw = row.get(f"{prefix}absenceDt", "")
        seme = row.get(f"{prefix}seme")
        if not date_tw:
            continue

        parts = date_tw.split("/")
        if len(parts) != 3:
            continue
        try:
            yr = int(parts[0]) + 1911
            month = int(parts[1])
            day = int(parts[2])
            date_str = f"{yr}/{month}/{day}"
            weekday = weekday_map[datetime.date(yr, month, day).weekday()]
        except Exception:
            continue

        term = seme_map.get(seme, "上")

        for i in range(1, 10):
            code = row.get(f"{prefix}lesson{i}")
            if not code:
                continue
            cell = absence_code_map.get(str(code))
            if not cell:
                continue
            records.append({
                "academic_term": term,
                "date": date_str,
                "weekday": weekday,
                "period": lesson_period_map[i],
                "cell": cell,
            })
        '''
        for field, period_name in [("morn", "早")]:
            code = row.get(f"{prefix}{field}")
            if not code:
                continue
            cell = absence_code_map.get(str(code))
            if not cell:
                continue
            records.append({
                "academic_term": term,
                "date": date_str,
                "weekday": weekday,
                "period": period_name,
                "cell": cell,
            })
        '''

    return records


def parse_semester_grades(first_semester_grades, second_semester_grades):
    """
    解析學期成績
    """
    subjects = {}

    def add_rows(data, semester_key):
        for row in (data or {}).get("dataRows", []):
            subj = row.get("subjId", "")
            if not subj:
                continue
            if subj not in subjects:
                subjects[subj] = {
                    "subject": subj,
                    "first_semester": {"type": "", "credits": "", "score": ""},
                    "second_semester": {"type": "", "credits": "", "score": ""},
                }
            score = row.get("score")
            credits = row.get("credits")
            subjects[subj][semester_key] = {
                "type": "",
                "credits": str(int(credits)) if credits is not None else "",
                "score": str(int(score)) if score is not None else "",
            }

    add_rows(first_semester_grades, "first_semester")
    add_rows(second_semester_grades, "second_semester")

    subject_scores = []
    for data in subjects.values():
        s1 = data["first_semester"]["score"]
        s2 = data["second_semester"]["score"]

        if s1 and s2:
            avg = (float(s1) + float(s2)) / 2
            data["annual_score"] = str(int(avg)) if avg % 1 == 0 else str(avg)
        elif s1:
            data["annual_score"] = s1
        elif s2:
            data["annual_score"] = s2
        else:
            data["annual_score"] = ""

        subject_scores.append(data)

    return subject_scores