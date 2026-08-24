import json
from urllib.parse import urlparse
from utils.v2 import get_request_verification_token
import requests


# 允許自動審核
def get_vesion(login_url):

    url = urlparse(login_url)
    try:
        data = requests.get(login_url).text

        if "Auth/Content/Images/shinherLogo.png" in data:
            return "v3"

        if "image/LoginPage/SchoolName.gif" in data or "shCaptchaImage" in data:
            return "v1"
    except Exception as e:
        print(e)
        pass
    # v1
    if url.path in ["/auth/Online", "/online"]:
        return "v1"

    # v2
    if url.path in ["/B2K2017/login.aspx"]:
        return "v2"

    # v3
    if url.path in ["/Auth/Auth/CloudLogin", "/Auth/Auth/Login"]:
        return "v3"

    # v4
    if "/#/login" in login_url:
        return "v4"

    # v6
    if url.path in ["/Login.action","/ecampus_KH/Login.action"] and url.hostname in [
        "hschool-mlife.k12ea.gov.tw",
        "hschool-mlife.k12ea.gov.tw",
        "sschool.tp.edu.tw",
        "tchs.mlife.org.tw"
    ]:
        return "v6"

    # v5
    if url.path in ["/Login.action"]:
        return "v5"

    # v7
    if url.path in ["/SCH_UI"]:
        return "v7"

    # v8
    if url.hostname in ["hsa.k12.ntut.edu.tw","portal.k12.ntut.edu.tw"]:
        return "v8"

    # v9
    if url.path in ["/skyweb"]:
        return "v9"

    print(url.hostname, url.path)
    return None


def v3(url):
    token_html = requests.get(durl).text
    token = get_request_verification_token(token_html)
    b = {"areaName": "", "__RequestVerificationToken": token}
    codedata = requests.post(
        url.replace("Login", "GetCloudSchoolNoList"), data=b
    ).json()
    print(codedata[0]["Value"])



def test():
    with open("school.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for i in data:
        durl = data[i]["api"] + data[i]["url"]["login"]
        vision = get_vesion(durl)
        if vision != data[i]["vision"]:
            print(f"{i} vision is {vision}, but school.json vision is {data[i]['vision']}")
