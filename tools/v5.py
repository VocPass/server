def get_allschool():
    s = """<area id="_100" href="#" shape="polygon" title="中正 zhongzheng" coords="129, 320, 118, 351, 121, 358, 132, 363, 132, 368, 147, 371, 170, 394, 180, 388, 149, 360, 155, 342, 171, 342, 170, 323"/>
<area id="_103" href="#" shape="polygon" title="大同 datong" coords="114, 243, 105, 314, 117, 311, 127, 316, 145, 318, 149, 266"/>
<area id="_104" href="#" shape="polygon" title="中山 zhongshan" coords="215, 251, 204, 251, 207, 262, 189, 262, 190, 321, 149, 316, 153, 268, 158, 273, 159, 253, 163, 253, 186, 237, 194, 240, 209, 233, 214, 237"/>
<area id="_105" href="#" shape="polygon" title="松山 songshan" coords="194, 320, 194, 266, 212, 266, 209, 254, 219, 254, 219, 249, 222, 249, 222, 270, 228, 270, 238, 266, 238, 287, 241, 290, 258, 286, 241, 301, 241, 308, 251, 309, 252, 312, 234, 311, 217, 325"/>
<area id="_106" href="#" shape="polygon" title="大安 daan" coords="193, 394, 213, 385, 227, 394, 228, 391, 207, 361, 216, 352, 216, 329, 175, 323, 175, 346, 158, 346, 154, 359, 186, 388, 185, 394"/>
<area id="_108" href="#" shape="polygon" title="萬華 wanhua" coords="78, 328, 99, 319, 116, 315, 125, 320, 114, 350, 116, 359, 126, 366, 128, 366, 128, 370, 123, 372, 114, 379, 111, 385, 97, 395, 78, 367"/>
<area id="_110" href="#" shape="polygon" title="信義 xinyi" coords="251, 379, 246, 379, 233, 388, 230, 387, 212, 361, 221, 355, 220, 328, 236, 315, 253, 316, 254, 324, 267, 333, 267, 340, 272, 347"/>
<area id="_111" href="#" shape="polygon" title="士林 shilin" coords="247, 38, 286, 179, 142, 257, 94, 221, 56, 216, 45, 199, 70, 201, 93, 190, 114, 226, 136, 228, 150, 213, 175, 144, 200, 140"/>
<area id="_112" href="#" shape="polygon" title="北投 beitou" coords="43, 172, 43, 191, 64, 196, 94, 185, 108, 195, 115, 218, 135, 225, 169, 139, 198, 132, 229, 36, 216, 11, 205, 33, 194, 32, 194, 47, 159, 62, 149, 85, 123, 80, 93, 122, 81, 123, 51, 159, 51, 173"/>
<area id="_114" href="#" shape="polygon" title="內湖 neihu" coords="282, 190, 313, 205, 327, 219, 332, 220, 331, 232, 338, 238, 338, 247, 319, 281, 309, 281, 307, 291, 285, 296, 283, 289, 273, 289, 273, 297, 265, 304, 245, 305, 259, 292, 265, 279, 243, 286, 242, 259, 227, 266, 226, 245, 219, 245, 219, 236, 212, 231, 218, 224, 225, 224, 245, 207, 260, 209, 266, 197"/>
<area id="_115" href="#" shape="polygon" title="南港 nangang" coords="277, 292, 280, 292, 280, 300, 294, 300, 312, 294, 314, 286, 319, 286, 336, 305, 324, 305, 319, 313, 320, 325, 329, 335, 370, 356, 391, 357, 397, 351, 404, 355, 404, 362, 380, 362, 374, 365, 370, 362, 348, 362, 338, 371, 301, 371, 293, 381, 259, 384, 256, 380, 276, 347, 271, 340, 271, 332, 258, 322, 259, 314, 254, 309, 267, 307, 277, 301"/>
<area id="_116" href="#" shape="polygon" title="文山 wenshan" coords="169, 415, 175, 405, 171, 398, 182, 391, 182, 399, 192, 399, 213, 390, 226, 399, 248, 383, 252, 383, 257, 388, 284, 385, 283, 395, 291, 404, 291, 420, 302, 431, 292, 440, 295, 457, 312, 457, 325, 471, 288, 487, 282, 474, 275, 479, 252, 470, 241, 477, 227, 476, 204, 433, 196, 444, 192, 441, 195, 435, 186, 430, 187, 419"/>"""
    cs = []
    for i in s.splitlines():
        a = i.strip().split(" ")[3][5:-1]
        d = i.strip().split(" ")[1][4:-1]
        cs.append((a, d))

    import requests

    new_schools = {}

    for i, j in cs:
        data = {
            "dist": j,
        }

        response = requests.post("https://sschool.tp.edu.tw/School.action", data=data)

        rd = response.json().get("parameterMap", {})
        for k in rd:
            if k.isdigit():
                if "測試" in rd[k]["name"]:
                    continue
                new_schools[rd[k]["name"]] = rd[k]["no"]
        print(".", end="")
    print(new_schools)


def write_school_json():
    # 先簡寫
    new_schools = {
        "新民中學": "351301",
        "建國中學": "353301",
        "成功中學": "353302",
        "北一女中": "353303",
        "靜修高中": "361301",
        "明倫高中": "363301",
        "成淵高中": "363302",
        "大同高中": "341302",
        "中山女中": "343301",
        "大同高中": "343302",
        "大直高中": "343303",
        "非學校型態實驗教育學校": "343F99",
        "西松高中": "313301",
        "中崙高中": "313302",
        "師大附中": "330301",
        "延平中學": "331301",
        "金甌女中": "331302",
        "復興實驗高中": "331304",
        "和平高中": "333301",
        "芳和實驗中學": "333304",
        "立人高中": "371301",
        "華江高中": "373301",
        "大理高中": "373302",
        "協和祐德高中": "321399",
        "松山高中": "323301",
        "永春高中": "323302",
        "泰北高中": "411301",
        "衛理女中": "411302",
        "華興中學": "411303",
        "陽明高中": "413301",
        "百齡高中": "413302",
        "薇閣高中": "421301",
        "幼華高中": "421302",
        "奎山實驗中學": "421303",
        "復興高中": "423301",
        "中正高中": "423302",
        "文德女中": "401301",
        "方濟中學": "401302",
        "達人高中": "401303",
        "內湖高中": "403301",
        "麗山高中": "403302",
        "南湖高中": "403303",
        "南港高中": "393301",
        "育成高中": "393302",
        "政大附中": "380301",
        "東山高中": "381301",
        "滬江高中": "381302",
        "大誠高中": "381303",
        "再興中學": "381304",
        "景文高中": "381305",
        "靜心高中": "381306",
        "景美女中": "383301",
        "萬芳高中": "383302",
        "數位實驗高級中學": "383303",
    }
    import json

    with open("school.json", "r", encoding="utf-8") as f:
        school = json.load(f)

    for i in new_schools:

        school[i] = {
            "vision": "v6",
            "app": 1.4,
            "beta": False,
            "api": "https://sschool.tp.edu.tw",
            "url": {
                "login": f"/Login.action?schNo={new_schools[i]}",
                "logined": "/PersonalWidget_getMyWidget.action",
                "root": "/",
            },
            "login": {
                "username": {"name": "account"},
                "password": {"name": "password"},
                "captcha": {},
                "captchaImage": {},
                "button": {"class": "btn_submit"},
                "successKeywords": ["登出", ',"page":1,'],
            },
            "route": {
                "merit_demerit": "/B0305S_Reward_select.action?dataName=vo",
                "attendance": "/B0209S_Absence_select.action",
                "exam_menu": "/A0410S_Item_select.action?syear={syear}&seme={seme}",
                "exam_results": "#",
                "semester_scores": "/A0410S_OpenStdView_selectA0410s.action?pId={pId}",
                "curriculum": "/myLessons.action",
                "info": "/A0410S_StdSemeView_select.action?statusM={statusM}&stdId={stdId}",
                "login": "/LoginInfo.action",
            },
        }

    with open("school.json", "w", encoding="utf-8") as f:
        json.dump(school, f, ensure_ascii=False, indent=4)

    print(len(new_schools))


# get_allschool()
write_school_json()
