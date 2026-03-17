from utils.base import *
import re
from bs4 import BeautifulSoup


def get_request_verification_token(html_content):
    """
    取得頁面中的 __RequestVerificationToken。
    """
    soup = BeautifulSoup(html_content, "html.parser")
    token_input = soup.find("input", {"name": "__RequestVerificationToken"})
    if not token_input:
        return None

    return token_input.get("value")


def parse_curriculum(curriculum_data):
    """
    解析課表
    """
    data = {}

    for item in curriculum_data['TimeTableItemList']:
        if not item.get('IsShow', False):
            continue
        subject = item.get('SubjectName', '')
        if not subject:
            continue
        weekday = num_to_chinese(item['WeekDay'])
        period = num_to_chinese(item['SectionSeq'])
        if not weekday or not period:
            continue
        if subject not in data:
            data[subject] = {'count': 0, 'schedule': []}
        data[subject]['schedule'].append({'weekday': weekday, 'period': period})
        data[subject]['count'] += 1

    return data


def parse_merit_demerit_records(records):
    """
    解析獎懲紀錄
    """
    good = ["大功", "小功", "嘉獎"]
    bad = ["大過", "小過", "警告"]

    data = [[], []]
    for record in records["Result"]:
        d = {
                    "date_occurred": record['MeritPenaltyDateDisplayString'],
                    "date_approved": record['MeritPenaltyCheckDateDisplayString'],
                    "reason": record['MertipenaltyReason'],
                    "action": f"{record['MertiPenaltyText']}{record['MertiPenaltyCount']}次",
                    "date_revoked": record['MertipenaltyCleanDate'],
                    "year": record['MertipenaltyYearTerm'],
                }
        if record["MertiPenaltyText"] in good:
            data[0].append(d)
        elif record["MertiPenaltyText"] in bad:
            data[1].append(d)

    return data


def parse_semester_grades(semester_grades):
    semester_grades = semester_grades["Result"]
    data = {
        "student_info": semester_grades["StudentName"],
        "subject_scores": [],
    }

    for course in semester_grades["SubjectScoreList"]:
        data["subject_scores"].append(
            {
                "subject": course["SubjectName"],
                "first_semester": {
                    "type": course["UpperSubjectCourseProperty"],
                    "credits": course["UpperSemesterCrieditDisplay"],
                    "score": course["UpperSemesterScoreDisplay"],
                },
                "second_semester": {
                    "type": course["DownSubjectCourseProperty"],
                    "credits": course["DownSemesterCrieditDisplay"],
                    "score": course["DownSemesterScoreDisplay"],
                },
                "annual_score": course["YearScore"],
            },
        )
    return data


def daily_performance_evaluation(dp):
    text = ""
    for i in range(1, 6):
        text += f'{dp[f"小項10{i}標題"].replace(" ", "")}：{dp[f"小項10{i}內容"].replace(" ", "")}<br/>'
    return text


def parse_daily_performance(daily_performance, year=1):
    """日常表現"""
    dp = daily_performance["Result"][year - 1 : year + 1]
    data = {
        "first_semester": {
            "daily_life_performance": {
                "evaluation": daily_performance_evaluation(dp[0]),
                "description": dp[0]["大項1內容"],
            },
            "service_learning": dp[0]["大項2內容"],
            "special_achievements": dp[0]["大項3內容"],
            "suggestions_and_comments": dp[0]["大項4內容"],
            "others": dp[0]["大項5內容"],
        },
        "second_semester": {
            "daily_life_performance": {
                "evaluation": daily_performance_evaluation(dp[1]),
                "description": dp[1]["大項1內容"],
            },
            "service_learning": dp[1]["大項2內容"],
            "special_achievements": dp[1]["大項3內容"],
            "suggestions_and_comments": dp[1]["大項4內容"],
            "others": dp[1]["大項5內容"],
        },
    }
    return data


def parse_absence_records(absence, t):
    """
    解析出勤紀錄
    """
    data = []
    for record in absence["Result"]["absentDetailList"]:
        m = record["AbsentDateDisplayText"][-2]
        for j in record["AbsentSectionList"]:
            if chinese_to_num(j["SectionName"]) == -1:
                # 午休不算吧？
                continue
            data.append(
                {
                    "academic_term": t,
                    "date": j["AbsentDate"].replace("-", "/").split("T")[0],
                    "weekday": m,
                    "period": chinese_to_num(j["SectionName"]),
                    "cell": j["AbsentText"],
                }
            )
    return data
