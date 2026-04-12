from fastapi import APIRouter, Response, Request, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from utils.pb import *

import os
import json
import aiohttp
import utils.v1 as v1
from utils.http_client import HttpsClient
import urllib.parse
import pocketbase
from pocketbase.models import FileUpload

with open("wallpaper_template.json", "r", encoding="utf-8") as f:
    template = json.load(f)

load_dotenv()
router = APIRouter(prefix="/api/wallpaper", tags=["桌布產生器"])


@router.get("/curriculum", summary="獲取課表模板")
async def get_curriculum_template(request: Request, response: Response):
    data = request.app.state.response
    try:
        data["code"] = 200
        data["message"] = "Success."
        data["data"] = template
        return data
    except Exception as e:
        print(f"Error loading wallpaper template: {e}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data["code"] = 500
        data["message"] = "Failed to load wallpaper template."
        data["data"] = None
        return data


@router.get("/font", summary="獲取字體文件")
async def get_font(request: Request, response: Response):
    font_url = "https://cdn.vocpass.com/font/"
    fonts = {
        "台北黑體": f"{font_url}TaipeiSansTCBeta-Regular.ttf",
        "得意黑": f"{font_url}SmileySans-Oblique.ttf",
        "大波浪圓體": f"{font_url}PopGothicCjkTc-Regular.ttf",
        "铁蒺藜体": f"{font_url}TiejiliSC-Regular.ttf",
        "寒蝉点阵体": f"{font_url}ChillBitmap_16px.ttf",
    }
    data = request.app.state.response
    data["code"] = 200
    data["message"] = "Success."
    data["data"] = fonts
    return data
