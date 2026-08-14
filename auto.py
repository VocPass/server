import json
from utils.v2 import get_request_verification_token
import requests


def v3(url):
    token_html = requests.get(durl).text
    token = get_request_verification_token(token_html)
    b={
        "areaName":"",
        "__RequestVerificationToken":token
        }
    codedata = requests.post(url.replace("Login","GetCloudSchoolNoList"),data=b).json()
    print(codedata[0]['Value'])
