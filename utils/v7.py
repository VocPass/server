import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def parse_select(html, select_id):
    """解析指定 <select> 的所有 <option>，回傳 {"text": "value"}"""
    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", id=select_id)
    if not select:
        return {}
    return {
        opt.get_text(strip=True): opt["value"]
        for opt in select.find_all("option", value=True)
    }


def parse_href(html):
    """解析所有 <a> 標籤，回傳 {"title 或 text": "href"}"""
    soup = BeautifulSoup(html, "html.parser")
    return {
        a.get("title") or a.get_text(strip=True) or a.get("id") or a["href"]: a["href"]
        for a in soup.find_all("a", href=True)
    }


def parse_iframes(html):
    """解析所有 <iframe> 標籤，回傳 {"id 或 src": "src"}"""
    soup = BeautifulSoup(html, "html.parser")
    return {
        (iframe.get("id") or iframe["src"]): iframe["src"]
        for iframe in soup.find_all("iframe", src=True)
    }


def parse_links(html):
    """解析所有 __doPostBack 的 <a> 標籤，回傳 {"text": "EVENTTARGET"}"""
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    for a in soup.find_all("a", href=True):
        m = re.search(r"__doPostBack\('([^']+)'", a["href"])
        if m:
            result[a.get_text(strip=True)] = m.group(1)
    return result


def parse_inputs(html):
    """解析所有 <input> 標籤，回傳 {"name": "value"}"""
    soup = BeautifulSoup(html, "html.parser")
    return {
        inp["name"]: inp.get("value", "")
        for inp in soup.find_all("input")
        if inp.get("name")
    }


def parse_merit_demerit_records(records):
    """
    解析獎懲紀錄
    """
    num_map = {
        "1": "乙",
        "2": "貳",
        "3": "參",
        "4": "肆",
        "5": "伍",
        "6": "陸",
        "7": "柒",
        "8": "捌",
        "9": "玖",
    }

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

    def normalize_action(raw):
        m = re.match(r"(.+?)(\d+)次", raw)
        if not m:
            return raw
        name = m.group(1)
        cnt = m.group(2)
        return f"{name}{num_map.get(cnt, cnt)}次"

    merit_keywords = {"嘉獎", "小功", "大功"}
    demerit_keywords = {"警告", "小過", "大過"}

    merits = []
    demerits = []

    for html in records:
        soup = BeautifulSoup(html, "html.parser")

        # 從標題取得學年期 (e.g. "【一下】獎懲紀錄" → year=1122)
        grade_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}
        term_map = {"上": 1, "下": 2}
        year = ""
        title_span = soup.find(
            "span", class_="labTitle", string=re.compile(r"【.+】獎懲紀錄")
        )
        if title_span:
            tm = re.search(r"【(.)(.)\】", title_span.get_text())
            if tm:
                # 從 GrdStd1 找對應的學年
                grade_num = grade_map.get(tm.group(1), 0)
                term_num = term_map.get(tm.group(2), 0)
                row_idx = (
                    (grade_num - 1) * 2 + term_num + 1
                )  # ctl02=一上, ctl03=一下, ...
                year_input = soup.find(
                    "input", id=f"GrdStd1_ctl{row_idx:02d}_GrdStd1_setyear_hf"
                )
                term_input = soup.find(
                    "input", id=f"GrdStd1_ctl{row_idx:02d}_GrdStd1_setterm_hf"
                )
                if year_input and term_input:
                    year = f"{year_input.get('value', '')}{term_input.get('value', '')}"

        table = soup.find("table", id="GrdStd2")
        if not table:
            continue

        for tr in table.find_all("tr"):
            if "tblHeader" in tr.get("class", []):
                continue
            cells = tr.find_all("td")
            if len(cells) < 5:
                continue

            date_raw = cells[0].get_text(strip=True)
            date_match = re.match(r"(\d+/\d+/\d+)", date_raw)
            date_str = tw_date_to_str(date_match.group(1)) if date_match else None

            reason = cells[1].get_text(strip=True)
            action_raw = cells[2].get_text(strip=True)
            action = normalize_action(action_raw)
            revoked = cells[4].get_text(strip=True) or None
            if revoked:
                revoked = tw_date_to_str(revoked)

            entry = {
                "date_occurred": date_str,
                "date_approved": None,
                "reason": reason,
                "action": action,
                "date_revoked": revoked,
                "year": year,
            }

            if any(k in action_raw for k in merit_keywords):
                merits.append(entry)
            elif any(k in action_raw for k in demerit_keywords):
                demerits.append(entry)

    return [merits, demerits]


def parse_absence_records(absence):
    """
    解析出勤紀錄
    """
    period_map = {
        "第一節": "1",
        "第二節": "2",
        "第三節": "3",
        "第四節": "4",
        "第五節": "5",
        "第六節": "6",
        "第七節": "7",
        "第八節": "8",
    }

    soup = BeautifulSoup(absence, "html.parser")
    table = soup.find("table", id="GrdStd2")
    if not table:
        return []
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    records = []
    for tr in table.find_all("tr"):
        if "tblHeader" in tr.get("class", []):
            continue
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not cells:
            continue
        row = dict(zip(headers, cells))

        date_raw = row.get("日期", "")
        m = re.match(r"(\d+)/(\d+)/(\d+)\((.)\)", date_raw)
        if not m:
            continue
        yr = int(m.group(1)) + 1911
        month = int(m.group(2))
        day = int(m.group(3))
        weekday = m.group(4)
        date_str = f"{yr}/{month}/{day}"
        academic_term = "上" if month >= 8 or month <= 1 else "下"

        for header, period in period_map.items():
            cell = row.get(header, "")
            if cell:
                records.append(
                    {
                        "academic_term": academic_term,
                        "date": date_str,
                        "weekday": weekday,
                        "period": period,
                        "cell": cell,
                    }
                )
    return records


def parse_curriculum(raw):
    """
    解析課表
    """
    weekday_map = {
        "1": "一",
        "2": "二",
        "3": "三",
        "4": "四",
        "5": "五",
        "6": "六",
        "7": "日",
    }
    period_map = {
        "1": "一",
        "2": "二",
        "3": "三",
        "4": "四",
        "5": "五",
        "6": "六",
        "7": "七",
        "8": "八",
    }
    time_map = {
        "1": ("08:10", "09:00"),
        "2": ("09:10", "10:00"),
        "3": ("10:10", "11:00"),
        "4": ("11:10", "12:00"),
        "5": ("13:10", "14:00"),
        "6": ("14:10", "15:00"),
        "7": ("15:10", "16:00"),
        "8": ("16:10", "17:00"),
    }

    soup = BeautifulSoup(raw, "html.parser")
    table = soup.find("table", id="GrdStd1")
    if not table:
        return {}

    result = {}
    for tr in table.find_all("tr"):
        if "tblHeader" in tr.get("class", []):
            continue
        cells = tr.find_all("td")
        if len(cells) < 6:
            continue

        name = cells[0].get_text(strip=True)
        teacher = cells[3].get_text(strip=True) or None
        room = cells[4].get_text(strip=True) or None
        time_text = cells[5].get_text(strip=True)

        # parse "每週:2-6,2-7,3-7" or "[1-15]週:1-6,1-7"
        m = re.search(r"週[：:](.+)", time_text)
        if not m:
            continue

        slots = []
        for pair in m.group(1).split(","):
            parts = pair.strip().split("-")
            if len(parts) != 2:
                continue
            w, p = parts
            start, end = time_map.get(p, ("", ""))
            slots.append(
                {
                    "weekday": weekday_map.get(w, w),
                    "period": period_map.get(p, p),
                    "start": start,
                    "end": end,
                    "teacher": teacher,
                    "room": room,
                }
            )

        if name in result:
            result[name]["count"] += len(slots)
            result[name]["schedule"].extend(slots)
        else:
            result[name] = {"count": len(slots), "schedule": slots}

    return result


def parse_semester_grades(semester_grades):
    """
    解析學期成績
    """
    compulsory_map = {"部": "必修", "校": "選修"}

    soup = BeautifulSoup(semester_grades, "html.parser")
    table = soup.find("table", id="GrdStd_GradeScore")
    if not table:
        return {"subject_scores": []}

    subjects = []
    for tr in table.find_all("tr"):
        if "tblHeader" in tr.get("class", []):
            continue
        cells = tr.find_all("td")
        if len(cells) < 10:
            continue

        def get_text(cell, field):
            span = cell.find("span", id=re.compile(rf"{field}_lab"))
            if not span:
                return ""
            return span.get_text(strip=True)

        # 各欄位的 ctl 編號來自 row 的 id
        first_div = cells[0].find("div", id=True)
        if not first_div:
            continue
        prefix = first_div["id"].rsplit("_course_name", 1)[0]

        name = get_text(cells[0], f"{prefix}_course_name")
        credit = get_text(cells[1], f"{prefix}_credit")
        compulsory_raw = get_text(cells[2], f"{prefix}_compulsory")
        compulsory = compulsory_map.get(compulsory_raw, compulsory_raw)

        score_term1 = get_text(cells[3], f"{prefix}_ScoreTerm1")
        score_makup1 = get_text(cells[4], f"{prefix}_ScoreMakup1")
        score_re1 = get_text(cells[5], f"{prefix}_ScoreRe1")

        score_term2 = get_text(cells[6], f"{prefix}_ScoreTerm2")
        score_makup2 = get_text(cells[7], f"{prefix}_ScoreMakup2")
        score_re2 = get_text(cells[8], f"{prefix}_ScoreRe2")

        has_sem1 = bool(score_term1)
        has_sem2 = bool(score_term2)

        def best_score(score, makup, retake):
            vals = [float(s) for s in (score, makup, retake) if s]
            return max(vals) if vals else None

        def fmt(v):
            if v is None:
                return ""
            return str(int(v)) if v == int(v) else str(v)

        def build_semester(has, score, makup, retake):
            if not has:
                return {"type": compulsory, "credits": "", "score": ""}
            return {
                "type": compulsory,
                "credits": credit,
                "score": fmt(best_score(score, makup, retake)),
            }

        best1 = best_score(score_term1, score_makup1, score_re1) if has_sem1 else None
        best2 = best_score(score_term2, score_makup2, score_re2) if has_sem2 else None
        bests = [b for b in (best1, best2) if b is not None]
        annual = sum(bests) / len(bests) if bests else None

        subjects.append(
            {
                "subject": name,
                "first_semester": build_semester(
                    has_sem1, score_term1, score_makup1, score_re1
                ),
                "second_semester": build_semester(
                    has_sem2, score_term2, score_makup2, score_re2
                ),
                "annual_score": fmt(annual),
            }
        )

    return {"subject_scores": subjects}


def parse_exam_results(exam):
    """
    解析考試成績
    """
    compulsory_map = {"部": "必修", "校": "選修"}

    soup = BeautifulSoup(exam, "html.parser")

    # 考試別 & 學年期 from dropdowns
    exam_ddl = soup.find("select", id="DdlStd_exam_no_ddl")
    exam_name = ""
    if exam_ddl:
        selected = exam_ddl.find("option", selected=True)
        if selected:
            exam_name = selected.get_text(strip=True)

    yearterm_ddl = soup.find("select", id="DdlStd_yearterm_ddl")
    yearterm_name = ""
    if yearterm_ddl:
        selected = yearterm_ddl.find("option", selected=True)
        if selected:
            yearterm_name = selected.get_text(strip=True)

    exam_info = f"[{yearterm_name}] {exam_name}" if yearterm_name or exam_name else ""

    # 科目成績表
    table = soup.find("table", id="GrdStd_Score")
    subjects = []
    if table:
        for tr in table.find_all("tr"):
            if "tblHeader" in tr.get("class", []):
                continue
            cells = tr.find_all("td")
            if len(cells) < 6:
                continue

            def get_span(cell, field):
                span = cell.find("span", id=re.compile(rf"{field}_lab"))
                if not span:
                    return ""
                return span.get_text(strip=True)

            first_div = cells[0].find("div", id=True)
            if not first_div:
                continue
            prefix = first_div["id"].rsplit("_course_name", 1)[0]

            name = get_span(cells[0], f"{prefix}_course_name")
            credit = get_span(cells[1], f"{prefix}_credit")
            compulsory_raw = get_span(cells[2], f"{prefix}_compulsory")
            compulsory = compulsory_map.get(compulsory_raw, compulsory_raw)
            score = get_span(cells[3], f"{prefix}_score")
            class_rank = get_span(cells[4], f"{prefix}_class_rank")
            grade_rank = get_span(cells[5], f"{prefix}_grade_rank")

            subjects.append(
                {
                    "subject": name,
                    "credit": credit,
                    "compulsory": compulsory,
                    "personal_score": score,
                    "class_rank": class_rank,
                    "grade_rank": grade_rank,
                }
            )

    total_score = 0.0
    total_credit = 0.0
    weighted_sum = 0.0
    for s in subjects:
        try:
            score_val = float(s["personal_score"])
            credit_val = float(s["credit"])
            total_score += score_val
            weighted_sum += score_val * credit_val
            total_credit += credit_val
        except (ValueError, TypeError):
            continue

    average_score = round(weighted_sum / total_credit, 2) if total_credit > 0 else 0

    return {
        "exam_info": exam_info,
        "subjects": subjects,
        "summary": {
            "totalScore": str(total_score),
            "averageScore": str(average_score),
            
            "total_score": str(total_score),
            "average_score": str(average_score),
            "class_rank": "",
            "department_rank": "",
        },
    }
