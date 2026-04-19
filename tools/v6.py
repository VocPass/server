a = """064328 新社高中
193301 臺中女中
193302 臺中一中
194303 臺中二中"""
import json

with open("school.json", "r", encoding="utf-8") as f:
    school = json.load(f)

for i in a.splitlines():
    code, name = i.split(" ")
    if name.strip() in school:
        print(f"{name.strip()} already in school.json, skipped.")
        # continue
    school[name.strip()] = {
        "vision": "v6",
        "app": 1.4,
        "beta": False,
        "api": "https://tchs.mlife.org.tw",
        "url": {
            "login": f"/Login.action?schNo={code}",
            "logined": "/PersonalWidget_getMyWidget.action",
            "root": "/",
        },
        "login": {
            "username": {"name": "loginId"},
            "password": {"name": "pas1"},
            "captcha": {"name":"validateCode"},
            "captchaImage": {
                "selector": "img-fluid",
                "type": "class"
            },
            "button": {"class": "btn btn-orange btn-block rounded-pill"},
            "successKeywords": ["登入者"],
        },
        "route": {
            "merit_demerit": "/B0305S_Reward_select.action?dataName=vo",
            "attendance": "/B0209S_Absence_select.action",
            "exam_menu": "/A0410S_Item_select.action?syear={syear}&seme={seme}",
            "exam_results": "#",
            "semester_scores": "/A0410S_OpenStdView_selectA0410s.action?pId={pId}",
            "curriculum": "#",
            "info": "/A0410S_StdSemeView_select.action?statusM={statusM}&stdId={stdId}",
        },
    }

with open("school.json", "w", encoding="utf-8") as f:
    json.dump(school, f, ensure_ascii=False, indent=4)