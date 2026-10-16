"""新北高中職校務：將 HSA 查詢頁轉換成 demo 的資料格式。"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup

EXAMS = {"1": "定期一成績", "2": "定期二成績", "3": "期末考成績", "4": "平時成績"}
CELL_MAP = {
    "曠課": "曠", "病假": "病", "事假": "事", "遲到": "遲", "早退": "早退",
    "公假": "公", "喪假": "喪", "生理假": "生理", "身心調適假": "身心",
    "其他特殊事故": "其他", "產前假": "產前", "娩假": "娩", "流產假": "流產",
    "育嬰假": "育嬰", "婚假": "婚", "陪產假": "陪產", "缺課(缺席)": "缺",
}
CHINESE_NUMBERS = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
                   "六": "6", "七": "7", "八": "8", "九": "9", "十": "10",
                   "十一": "11", "十二": "12"}


def parse_options(html, selector):
    soup = BeautifulSoup(html, "html.parser")
    return [o["value"] for o in soup.select(f"{selector} option[value]") if o["value"].isdigit()]


def parse_merit_demerit_records(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.gridtable")
    if table is None:
        raise ValueError("Missing merit/demerit table.")
    records = [[], []]
    for row in table.select("tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 4:
            continue
        values = [c.get_text(" ", strip=True) for c in cells]
        term = re.search(r"(\d+)\s*(上|下)學期", values[0])
        occurred = re.fullmatch(r"(\d+)-(\d+)-(\d+)", values[1])
        if not term or not occurred:
            continue
        stamp = f"{int(occurred[1]) + 1911}/{occurred[2]}/{occurred[3]}"
        span = cells[2].find("span")
        action = (span or cells[2]).get_text(" ", strip=True)
        action = re.sub(r"^項目[：:]\s*", "", action)
        group = 0 if any(k in action for k in ("嘉獎", "小功", "大功")) else 1
        if not any(k in action for k in ("嘉獎", "小功", "大功", "警告", "小過", "大過")):
            continue
        revoked = re.search(r"(?:銷過|撤銷).*?(\d+)[-/](\d+)[-/](\d+)", values[2])
        records[group].append({
            "date_occurred": stamp, "date_approved": stamp, "reason": values[3],
            "action": action,
            "date_revoked": f"{int(revoked[1]) + 1911}/{revoked[2]}/{revoked[3]}" if revoked else None,
            "year": term[1] + ("1" if term[2] == "上" else "2"),
        })
    return records


def parse_absence_records(html):
    soup = BeautifulSoup(html, "html.parser")
    table = next((t for t in soup.find_all("table")
                  if "缺曠日期" in t.get_text() and "節次" in t.get_text()
                  and not t.find("table")), None)
    if table is None:
        raise ValueError("Missing attendance table.")
    records = []
    for row in table.find_all("tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) != 4:
            continue
        values = [c.get_text("", strip=True) for c in cells]
        stamp = re.fullmatch(r"(\d+)/(\d+)/(\d+)", values[1])
        term = re.fullmatch(r"(\d+)/(上|下)", re.sub(r"\s+", "", values[0]))
        if not stamp or not term:
            continue
        day = date(int(stamp[1]) + 1911, int(stamp[2]), int(stamp[3]))
        for period in re.split(r"[,，、]", values[3]):
            period = period.strip()
            if not period:
                continue
            period = re.sub(r"^第(.+)節$", r"\1", period)
            records.append({
                "academic_term": term[2], "date": f"{day.year}/{day.month}/{day.day}",
                "weekday": "一二三四五六日"[day.weekday()],
                "period": CHINESE_NUMBERS.get(period, period), "cell": CELL_MAP.get(values[2], values[2]),
            })
    return records


def parse_score_table(html):
    soup = BeautifulSoup(html, "html.parser")
    table = next((t for t in soup.select("table.imagetable") if "課目名稱" in t.get_text()), None)
    if table is None:
        raise ValueError("Missing score table.")
    headers = [c.get_text(strip=True) for c in table.find("tr").find_all(["th", "td"])]
    subjects, summary, credits = [], {}, {}
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td", recursive=False)
        if not cells:
            continue
        text = cells[0].get_text(" ", strip=True)
        match = re.fullmatch(r"(.+?)\s*[（(](必修|選修)\s*[：:]\s*([\d.]+)[）)]", text)
        if match:
            subjects.append({"subject": match[1], "type": match[2], "credits": match[3],
                             "scores": {h: c.get_text(strip=True) for h, c in zip(headers[1:], cells[1:])}})
        elif len(cells) > 1:
            name = text.rstrip("：: ")
            summary[name] = {h: c.get_text(strip=True) for h, c in zip(headers[1:], cells[1:])}
    credit_table = next((t for t in soup.select("table.imagetable") if "應得學分數" in t.get_text()), None)
    if credit_table:
        row = next((r for r in credit_table.find_all("tr") if len(r.find_all("td", recursive=False)) == 6), None)
        if row:
            values = [c.get_text(strip=True) for c in row.find_all("td", recursive=False)]
            for i, name in enumerate(("應得學分", "實得學分", "實得累計")):
                try:
                    credits[name] = format(Decimal(values[i * 2]) + Decimal(values[i * 2 + 1]), "f")
                except InvalidOperation:
                    credits[name] = ""
    return {"subjects": subjects, "summary": summary, "credits": credits}


def parse_exam_menu(term_tables):
    menu = []
    for year, term, html in term_tables:
        parsed = parse_score_table(html)
        for key, label in EXAMS.items():
            if any(s["scores"].get(label) for s in parsed["subjects"]):
                menu.append({"name": f"{year}學年度{'上' if term == '1' else '下'}學期 {label}",
                             "url": f"{year}:{term}:{key}"})
    return menu


def parse_exam_results(html, exam, student_info=""):
    year, term, key = exam.split(":")
    label = EXAMS[key]
    parsed = parse_score_table(html)
    rank = parsed["summary"]
    return {
        "student_info": {"student_id": "", "name": student_info, "class": ""},
        "exam_info": f"{year}學年度{'上' if term == '1' else '下'}學期 {label}",
        "subjects": [{"subject": s["subject"], "personal_score": s["scores"][label], "class_average": ""}
                     for s in parsed["subjects"] if s["scores"].get(label)],
        "summary": {"totalScore": "", "averageScore": "", "total_scores": "", "average_scores": "",
                    "class_rank": rank.get("班級排名", {}).get(label, ""),
                    "department_rank": rank.get("類組排名", {}).get(label, "")},
    }


def parse_semester_grades(first_html, second_html, student_info=""):
    subjects, totals = {}, {}
    for key, html in (("first_semester", first_html), ("second_semester", second_html)):
        parsed = parse_score_table(html)
        for subject in parsed["subjects"]:
            name = subject["subject"]
            if name not in subjects:
                subjects[name] = {"subject": name, "first_semester": {"type": "", "credits": "", "score": ""},
                                  "second_semester": {"type": "", "credits": "", "score": ""}, "annual_score": ""}
            subjects[name][key] = {"type": subject["type"], "credits": subject["credits"],
                                   "score": subject["scores"].get("學期成績", "")}
        summary = {"學期平均": parsed["summary"].get("學期平均", {}).get("定期一成績", ""),
                   **parsed["credits"]}
        for source, label in (("班級排名", "學期名次"), ("類組排名", "類組名次"), ("年級排名", "年級名次")):
            summary[label] = parsed["summary"].get(source, {}).get("學期成績", "")
        for label, value in summary.items():
            totals.setdefault(label, {"first_semester": "", "second_semester": "", "annual": ""})[key] = value
    return {"student_info": student_info, "subject_scores": list(subjects.values()), "total_scores": totals,
            "daily_performance": {"first_semester": {}, "second_semester": {}}}
