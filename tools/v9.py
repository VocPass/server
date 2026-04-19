t = """光復高中(夜),https://night.kfsh.hc.edu.tw,/skyweb
苗栗高中,https://fs25.mlsh.mlc.edu.tw,/skyweb
穀保家商,https://web.kpvs.ntpc.edu.tw,/skyweb"""


import json

with open("school.json", "r", encoding="utf-8") as f:
    schools = json.load(f)
print(len(t.splitlines()))
for i in t.splitlines():
    name, url, login_url = i.split(",")
    d = {
        "vision": "v9",
        "app": 1.6,
        "beta": False,
        "api": url,
        "url": {"login": "/", "logined": "/f_head.asp", "root": ""},
        "login": {
            "username": {"name": "txtid"},
            "password": {"name": "txtpwd"},
            "captcha": {},
            "captchaImage": {},
            "button": {},
            "successKeywords": ["修改密碼", "使用說明", "f_left.asp"],
        },
        "route": {
            "merit_demerit": "/stu/stu_result6.asp",
            "attendance": "/stu/stu_result4.asp",
            "exam_menu": "#",
            "exam_results": "#",
            "semester_scores": "#",
            "curriculum": "/stu/lesson.asp",
        },
    }
    schools[name] = d
    print(f"Added {name}")

with open("school.json", "w", encoding="utf-8") as f:
    json.dump(schools, f, ensure_ascii=False, indent=4)
