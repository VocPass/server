from utils.base import *
import re
from bs4 import BeautifulSoup


def parse_merit_demerit_records(records):
    """
    解析獎懲紀錄
    """
    soup = BeautifulSoup(records, "html.parser")
    tables = soup.find_all("table")
    merits = []
    demerits = []

    if len(tables) < 4:
        return [merits, demerits]

    t3 = tables[3]
    current_section = None

    num_map = {"1": "乙", "2": "貳", "3": "參", "4": "肆", "5": "伍", "6": "陸", "7": "柒", "8": "捌", "9": "玖"}

    def tw_date_to_str(tw_date):
        m = re.match(r"(\d+)年(\d+)月(\d+)日", tw_date)
        if m:
            y = int(m.group(1)) + 1911
            return f"{y}/{int(m.group(2)):02d}/{int(m.group(3)):02d}"
        return tw_date

    for tr in t3.find_all("tr"):
        tds = [td.text.strip() for td in tr.find_all(["th", "td"])]
        if not tds:
            continue

        text = tds[0]
        if "歷年獎勵明細" in text:
            current_section = "merit"
            continue
        elif "歷年懲罰明細" in text:
            current_section = "demerit"
            continue

        if "簽呈日期" in text or "無紀錄" in text:
            continue

        if len(tds) >= 9:
            date_approved = tw_date_to_str(tds[0])
            date_occurred = tw_date_to_str(tds[1])
            reason = tds[2]

            action_parts = []
            if current_section == "merit":
                names = ["大功", "小功", "嘉獎", "優點"]
                for i in range(4):
                    if i + 4 < len(tds):
                        cnt = tds[i + 4]
                        if cnt.isdigit() and int(cnt) > 0:
                            action_parts.append(f"{names[i]}{num_map.get(cnt, cnt)}次")
            elif current_section == "demerit":
                names = ["大過", "小過", "警告", "缺點"]
                for i in range(4):
                    if i + 4 < len(tds):
                        cnt = tds[i + 4]
                        if cnt.isdigit() and int(cnt) > 0:
                            action_parts.append(f"{names[i]}{num_map.get(cnt, cnt)}次")

            action_str = " ".join(action_parts)

            year_val = ""
            m = re.match(r"(\d+)年", tds[1])
            if m:
                tw_y = int(m.group(1))
                year_val = str(tw_y - 1) + "1"

            record_obj = {
                "date_occurred": date_occurred,
                "date_approved": date_approved,
                "reason": reason,
                "action": action_str,
                "date_revoked": None,
                "year": year_val
            }
            if current_section == "merit":
                merits.append(record_obj)
            elif current_section == "demerit":
                demerits.append(record_obj)

    return [merits, demerits]


def parse_semester_grades(semester_grades, target_grade=None):
    soup = BeautifulSoup(semester_grades, "html.parser")

    student_info = ""
    current_grade_val = None

    t0 = soup.find("table")
    if t0:
        tds = t0.find_all("td")
        if len(tds) > 0:
            match = re.search(r"身份是\s*：\s*([\w\s]+)", tds[0].text)
            if match:
                student_info = match.group(1).strip()
            else:
                student_info = tds[0].text.strip()

        for td in tds:
            text = td.text.strip()
            if "學期" in text and "學年" in text:
                continue

            m1 = re.search(r"([1-3])\d{1,2}\s*[班A-Z甲乙丙丁]", text)
            if m1:
                current_grade_val = int(m1.group(1))
                break

            m2 = re.search(r"([一二三])\s*年", text)
            if m2:
                g_map = {"一": 1, "二": 2, "三": 3}
                current_grade_val = g_map[m2.group(1)]
                break

    tables = soup.find_all("table")
    years_data = {}

    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue

        first_cell = rows[0].find("td")
        if not first_cell:
            continue

        text = first_cell.text.strip()
        m = re.match(r"(\d+)\s*學年度\s*第\s*(\d+)\s*學期", text)
        if m:
            year = m.group(1)
            term = m.group(2)

            if year not in years_data:
                years_data[year] = {"subjects": {}, "eval1": {}, "eval2": {}, "tot1": {}, "tot2": {}}

            subject_started = False
            expected_row = None
            for row in rows:
                cols = [td.text.strip() for td in row.find_all("td")]
                if not cols:
                    continue

                if "科目名稱" in cols[0] and "課程類別" in cols:
                    subject_started = True
                    continue

                if "修習學分數" in cols and "必修學分數" in cols:
                    subject_started = False
                    expected_row = "credits"
                    continue
                elif expected_row == "credits":
                    years_data[year][f"tot{term}"]["修習學分數"] = cols[0] if len(cols) > 0 else ""
                    years_data[year][f"tot{term}"]["必修學分數"] = cols[1] if len(cols) > 1 else ""
                    years_data[year][f"tot{term}"]["選修學分數"] = cols[2] if len(cols) > 2 else ""
                    expected_row = None
                    continue

                if "實得修習學分數" in cols and "實得必修學分數" in cols:
                    subject_started = False
                    expected_row = "earned_credits"
                    continue
                elif expected_row == "earned_credits":
                    years_data[year][f"tot{term}"]["實得修習學分數"] = cols[0] if len(cols) > 0 else ""
                    years_data[year][f"tot{term}"]["實得必修學分數"] = cols[1] if len(cols) > 1 else ""
                    years_data[year][f"tot{term}"]["實得選修學分數"] = cols[2] if len(cols) > 2 else ""
                    expected_row = None
                    continue

                if "學業成績" in cols and "學業班級排名(班百分比)" in cols:
                    subject_started = False
                    expected_row = "rank"
                    continue
                elif expected_row == "rank":
                    years_data[year][f"tot{term}"]["學業成績"] = cols[0] if len(cols) > 0 else ""
                    years_data[year][f"tot{term}"]["學期名次"] = cols[1] if len(cols) > 1 else ""
                    expected_row = None
                    continue

                if subject_started:
                    if "學業成績" in cols:
                        idx = cols.index("學業成績")
                        if len(cols) > idx+4:
                            val = cols[idx+4]
                            if term == "1":
                                years_data[year]["tot1"]["學業成績"] = val
                            else:
                                years_data[year]["tot2"]["學業成績"] = val

                    elif "◎" in cols[0]:
                        name = cols[0].replace("◎", "").split("\n")[0].strip()
                        c_type = cols[1] if len(cols)>1 else ""
                        c_credit = cols[3] if len(cols)>3 else ""
                        c_score = cols[4] if len(cols)>4 else ""
                        if name not in years_data[year]["subjects"]:
                            years_data[year]["subjects"][name] = {"1": {"type": "", "credits": "", "score": ""}, "2": {"type": "", "credits": "", "score": ""}}
                        years_data[year]["subjects"][name][term] = {
                            "type": c_type,
                            "credits": c_credit,
                            "score": c_score
                        }

            eval_dict = {}
            for row in rows:
                cols = [td.text.strip() for td in row.find_all("td")]
                if "綜合表現" in cols:
                    idx = cols.index("綜合表現")
                    if len(cols) > idx+1: eval_dict["daily_life_performance_description"] = cols[idx+1]
                if "服務學習" in cols:
                    idx = cols.index("服務學習")
                    if len(cols) > idx+1: eval_dict["service_learning"] = cols[idx+1]
                if "具體建議" in cols:
                    idx = cols.index("具體建議")
                    if len(cols) > idx+1: eval_dict["suggestions_and_comments"] = cols[idx+1]
            if eval_dict:
                if term == "1": years_data[year]["eval1"] = eval_dict
                else: years_data[year]["eval2"] = eval_dict

    subject_scores = []

    daily_performance = {
        "first_semester": {
            "daily_life_performance": { "evaluation": "", "description": "" },
            "service_learning": "",
            "special_achievements": "",
            "suggestions_and_comments": "",
            "others": ""
        },
        "second_semester": {
            "daily_life_performance": { "evaluation": "", "description": "" },
            "service_learning": "",
            "special_achievements": "",
            "suggestions_and_comments": "",
            "others": ""
        }
    }

    total_scores = { }

    latest_year = max(years_data.keys(), key=int) if years_data else None

    selected_year = latest_year
    if target_grade is not None and years_data:
        sorted_years = sorted(years_data.keys(), key=int)
        idx = int(target_grade) - 1
        if 0 <= idx < len(sorted_years):
            selected_year = sorted_years[idx]
        else:
            selected_year = None
    elif current_grade_val is not None and years_data:
        
        sorted_years = sorted(years_data.keys(), key=int)
        idx = current_grade_val - 1
        if 0 <= idx < len(sorted_years):
            selected_year = sorted_years[idx]
        else:
            selected_year = None

    if selected_year:
        for name, terms in years_data[selected_year]["subjects"].items():
            s1 = terms["1"]
            s2 = terms["2"]
            annual = ""
            if s1["score"].isdigit() and s2["score"].isdigit():
                annual = str(round((float(s1["score"]) + float(s2["score"])) / 2, 1)).rstrip('0').rstrip('.')
            elif s1["score"].isdigit():
                annual = s1["score"]
            elif s2["score"].isdigit():
                annual = s2["score"]

            subject_scores.append({
                "subject": name,
                "first_semester": s1,
                "second_semester": s2,
                "annual_score": annual
            })

        y_data = years_data[selected_year]
        e1 = y_data.get("eval1", {})
        e2 = y_data.get("eval2", {})
        daily_performance = {
            "first_semester": {
                "daily_life_performance": { "evaluation": "", "description": e1.get("daily_life_performance_description", "") },
                "service_learning": e1.get("service_learning", ""),
                "special_achievements": "",
                "suggestions_and_comments": e1.get("suggestions_and_comments", ""),
                "others": ""
            },
            "second_semester": {
                "daily_life_performance": { "evaluation": "", "description": e2.get("daily_life_performance_description", "") },
                "service_learning": e2.get("service_learning", ""),
                "special_achievements": "",
                "suggestions_and_comments": e2.get("suggestions_and_comments", ""),
                "others": ""
            }
        }

        total_scores = {
            "學業成績": {
                "first_semester": y_data.get("tot1", {}).get("學業成績", ""),
                "second_semester": y_data.get("tot2", {}).get("學業成績", ""),
                "annual": ""
            },
            "實得學分": {
                "first_semester": y_data.get("tot1", {}).get("實得修習學分數", ""),
                "second_semester": y_data.get("tot2", {}).get("實得修習學分數", ""),
                "annual": ""
            },
            "學期名次(班百分比)": {
                "first_semester": y_data.get("tot1", {}).get("學期名次", ""),
                "second_semester": y_data.get("tot2", {}).get("學期名次", ""),
                "annual": ""
            }
        }

    return {
        "student_info": student_info,
        "subject_scores": subject_scores,
        "total_scores": total_scores,
        "daily_performance": daily_performance
    }

def daily_performance_evaluation(dp):
    pass

def parse_daily_performance(daily_performance, year=1):
    """日常表現"""
    grades = parse_semester_grades(daily_performance)
    return grades.get("daily_performance", {})

def parse_absence_records(absence):
    """
    解析出勤紀錄
    """
    import datetime
    import re

    soup = BeautifulSoup(absence, "html.parser")

    term_str = "上"
    t0 = soup.find("table")
    if t0:
        for td in t0.find_all("td"):
            text = td.text.strip()
            if "學年" in text and "學期" in text:
                if "第一學期" in text or "第1學期" in text or "上學期" in text:
                    term_str = "上"
                elif "第二學期" in text or "第2學期" in text or "下學期" in text:
                    term_str = "下"
                break

    tables = soup.find_all("table")
    records = []

    if len(tables) < 5:
        return records

    table = tables[4]
    rows = table.find_all("tr")
    if len(rows) <= 1:
        return records

    header = [td.text.strip() for td in rows[0].find_all(["th", "td"])]
    weekday_map = {0: "一", 1: "二", 2: "三", 3: "四", 4: "五", 5: "六", 6: "日"}

    for row in rows[1:]:
        cols = [td.text.strip() for td in row.find_all("td")]
        if len(cols) < len(header):
            continue

        date_tw = cols[2]
        if not date_tw:
            continue

        parts = date_tw.split('/')
        if len(parts) == 3:
            try:
                yr = int(parts[0]) + 1911
                month = int(parts[1])
                day = int(parts[2])
                date_str = f"{yr}/{month}/{day}"
                dt = datetime.date(yr, month, day)
                weekday = weekday_map[dt.weekday()]
            except:
                date_str = date_tw
                weekday = ""
        else:
            date_str = date_tw
            weekday = ""

        for idx in range(3, len(header)):
            period_name = header[idx]
            if not period_name.isdigit():
                continue

            cell_val = cols[idx]
            if cell_val and cell_val not in ["0", "未", ""]:
                records.append({
                    "academic_term": term_str,
                    "date": date_str,
                    "weekday": weekday,
                    "period": period_name,
                    "cell": cell_val
                })

    return records
