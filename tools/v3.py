sb = {
    "金門高中": "https://shcloud7.k12ea.gov.tw/KMSHKM",
    "德光高中": "https://shinher.tkgsh.tn.edu.tw/TKGSH",
    "復旦高中": "https://shinho.fdhs.tyc.edu.tw/FDSH",
    "曾文農工": "https://shcloud1.k12ea.gov.tw/TWIVSTN",
    "恆春工商": "https://shcloud13.k12ea.gov.tw/HCVSPTC",
    "觀音高中": "https://ssys.gish.tyc.edu.tw",
    "光復中學": "https://shinher.kfsh.hc.edu.tw/kfsh",
    "永靖高工": "https://shcloud7.k12ea.gov.tw/YJVSCHC",
    "振聲高中": "https://fxshap.fxsh.tyc.edu.tw",
    "澎湖海事": "https://shcloud12.k12ea.gov.tw/PHMHSPHC",
    "台南二中": "https://shcloud9.k12ea.gov.tw/TNSSHTN/?sys=Absent",
    "復旦高中": "https://shinho.fdhs.tyc.edu.tw/FDSH",
}


import json

with open("school.json", "r", encoding="utf-8") as f:
    school = json.load(f)

for i in sb:
    if i in school:
        
        continue
    school[i] = {
        "vision": "v3",
        "app": 1.0,
        "beta": False,
        "school_code": "{sb}",
        "api": sb[i],
        "url": {
            "login": "/Auth/Auth/Login",
            "logined": "/ICampus/Home/Index2",
            "root": "",
        },
        "login": {
            "username": {"name": "LoginId"},
            "password": {"name": "PassString"},
            "captcha": {},
            "captchaImage": {},
            "button": {"class": "loginBtnAdjust"},
            "successKeywords": ["智慧校園平台首頁"],
        },
        "route": {
            "merit_demerit": "/ICampus/TutorShSheMoralMeritPenalty/GetMeritPenaltyDetailsList",
            "attendance": "/ICampus/TutorShSheAbsentStatistics/GetTutorShSheAbsentDetails",
            "exam_menu": "#",
            "exam_results": "#",
            "semester_scores": "/ICampus/TutorShGrade/GetScoreForStudentGradeLevel",
            "curriculum": "/ClassTableV2/ClassTable/GetTimeTable",
            "info": "/ICampus/CommonData/GetStudentBasicInfo",
            "daily": "/ICampus/TutorShSheMoralMeritPenalty/GetDailyList",
        },
        "get": {
            "merit_demerit": "/ICampus/StudentInfo",
            "attendance": "/ICampus/StudentInfo",
            "exam_menu": "#",
            "exam_results": "#",
            "semester_scores": "/ICampus/StudentInfo/Index",
            "curriculum": "/ClassTableV2/ClassTable",
            "info": "/ICampus/StudentInfo",
        },
    }
    print(f"{i}: {school[i]['api']}{school[i]['url']['login']}")
    
with open("school.json", "w", encoding="utf-8") as f:
    json.dump(school, f, ensure_ascii=False, indent=4)
print(len(sb))