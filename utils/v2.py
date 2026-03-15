from utils.base import *


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
        