from utils.base import *
import re
from bs4 import BeautifulSoup


def parse_curriculum(curriculum_data):
    """
    解析課表
    """
    data = {}
    time = {}

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

    for first, second in zip(
        first_semester_grades["obj"]["DataList"],
        second_semester_grades["obj"]["DataList"],
    ):
        d = {
            "subject": first["OpTitle"],
            "first_semester": {
                "type": first["StudyType"],
                "credits": str(first["Credit"]),
                "score": "-",
            },
            "second_semester": {
                "type": second["StudyType"],
                "credits": str(second["Credit"]),
                "score": "-",
            },
            "annual_score": "-",
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
        