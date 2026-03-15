
def num_to_chinese(num):
    chinese_numerals = {
        0: "零",
        1: "一",
        2: "二",
        3: "三",
        4: "四",
        5: "五",
        6: "六",
        7: "七",
        8: "八",
        9: "九",
    }
    return chinese_numerals.get(num, "")


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