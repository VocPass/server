from datetime import datetime


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


class YearModel:
    def __init__(self, date):
        datetime_object = datetime.strptime(date, "%Y/%m/%d")
        # YYYY/MM/DD
        self.semester = (
            1 if datetime_object.month > 8 or datetime_object.month < 3 else 2
        )
        self.year = datetime_object.year - 1911 - (self.semester - 1)

    def to_dict(self):
        return {"year": self.year, "semester": self.semester}
