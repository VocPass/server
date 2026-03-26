import json


with open("school.json", "r", encoding="utf-8") as f:
    school = json.load(f)


d = {
    "樹人家商": "https://day.stgvs.ntpc.edu.tw",
    "育達高中": "https://ydsturec-web.yuda.tyc.edu.tw",
    "瀛海高中": "https://study.yhsh.tn.edu.tw",
    "東海高中": "https://grades.thhs.ntpc.edu.tw",
    "光華高中":"https://apps.khgs.tn.edu.tw",
    "君毅高中":"https://school.cish.mlc.edu.tw",
    "竹林中學":"https://score.clsh.ntpc.edu.tw",
    "慈濟高中":"https://stud.tcsh.tn.edu.tw"
}

for i in d:
    if i in school:
        continue
    school[i] = {
        "vision": "v1",
        "app": 1.0,
        "beta": False,
        "api": d[i],
        "url": {
            "login": "/online",
            "logined": "/online/student/frames.asp",
            "root": "/",
        },
        "login": {
            "username": {"name": "Loginid"},
            "password": {"name": "LoginPwd"},
            "captcha": {"name": "vcode"},
            "captchaImage": {"selector": "imgvcode", "type": "id"},
            "button": {"class": "Enter"},
            "successKeywords": ["學生線上查詢"],
        },
        "route": {
            "merit_demerit": "/online/selection_student/moralculture_%20bonuspenalty.asp",
            "attendance": "/online/selection_student/absentation_skip_school.asp",
            "exam_menu": "/online/selection_student/student_subjects_number.asp?action=open_window_frame",
            "exam_results": "/online/selection_student/{file_name}",
            "semester_scores": "/online/selection_student/year_accompliv1ment.asp?action=selection_underside_year&year_class={year_class}&number={number}",
            "curriculum": "/online/student/school_class_tabletime.asp",
        },
    }
with open("school.json", "w", encoding="utf-8") as f:
    json.dump(school, f, ensure_ascii=False, indent=4)