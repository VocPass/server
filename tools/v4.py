import json


with open("school.json", "r", encoding="utf-8") as f:
    school = json.load(f)

d = """羅東高中
蘇澳海事
頭城家商
關西高中
苗栗高中
苗栗高商
仁愛高農
新營高工
玉井工商
臺南高工
曾文高農
新營高工(夜)
臺南高工(夜)
旗美高中
佳冬高農
佳冬高農(夜)
臺東高中
新竹高商
臺中高農
臺中高農(夜)
馬祖高中"""


for i in d.splitlines():
    if i.strip() in school:
        print(f"{i.strip()} already in school.json, skipped.")
        continue
    school[i.strip()] = {
        "vision": "v4",
        "app": 1.3,
        "beta": False,
        "api": "https://kcsc.k12ea.gov.tw",
        "url": {"login": "/#/login", "logined": "/#/dashboard", "root": "/"},
        "login": {
            "username": {"name": "username"},
            "password": {"id": "pwd"},
            "captcha": {},
            "captchaImage": {},
            "button": {"class": "loginForm__btn"},
            "successKeywords": [" 主頁 "],
        },
        "route": {
            "merit_demerit": "/skyweb/skyweb_protal.asp?url=stu/stu_result6.asp&token={token}",
            "attendance": "/skyweb/skyweb_protal.asp?url=stu/stu_result3.asp&token={token}",
            "exam_menu": "#",
            "exam_results": "#",
            "semester_scores": "/skyweb/skyweb_protal.asp?url=stu/stu_result10.asp&token={token}",
            "curriculum": "#",
        },
    }
print(len(d.splitlines()))
with open("school.json", "w", encoding="utf-8") as f:
    json.dump(school, f, ensure_ascii=False, indent=4)
